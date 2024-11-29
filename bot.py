from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from telegram import Update
import pandas as pd
import os, codecs, datetime
from config.config import BotConfig
from modules.student_data_service import StudentDataService, StudentProgress
from modules.gpt_service import GPTService
from modules.logger import BotLogger

# Состояния диалога
WAITING_EMAIL = 1

class TelegramBot:
    def __init__(self, config: BotConfig):
        # Инициализация логгера
        self.logger = BotLogger(config.log_directory)
        self.logger.log_bot_startup(config.__dict__)

        # Инициализация хранения верифицированных пользователей
        self.verified_users_file = 'verified_users.csv'
        self.user_verified = self._load_verified_users()
        
        # Инициализация Telegram приложения
        self.application = Application.builder().token(config.bot_key).build()
        
        # Инициализация конфигурации
        self.config = config
        
        # Инициализация сервисов с передачей логгера
        self.student_service = StudentDataService(self.logger)
        self.gpt_service = GPTService(config, self.logger)
        
        # Инициализация состояния и данных
        self.user_verified = {}
        self.history = self._load_history()
        self.role = self._load_role()
        
        # Настройка обработчиков
        self._setup_handlers()
        
        # Логирование успешного запуска
        self.logger.logger.info('Bot initialization completed successfully')
        print('Запуск бота...')
        print(f'Настроено обновление данных каждую {self.config.update_interval} минуту')
        
        # Запуск бота
        self.application.run_polling(1.0)
    
    def _load_verified_users(self) -> dict:
        """Загрузка верифицированных пользователей из файла"""
        try:
            if os.path.exists(self.verified_users_file):
                df = pd.read_csv(self.verified_users_file)
                
                # Проверяем уникальность email и chat_id
                if df['email'].duplicated().any():
                    self.logger.logger.error("Duplicate emails found in verified_users.csv")
                    # Оставляем только первые вхождения для каждого email
                    df = df.drop_duplicates(subset=['email'], keep='first')
                
                if df['chat_id'].duplicated().any():
                    self.logger.logger.error("Duplicate chat_ids found in verified_users.csv")
                    # Оставляем только первые вхождения для каждого chat_id
                    df = df.drop_duplicates(subset=['chat_id'], keep='first')
                
                verified_users = {
                    int(row['chat_id']): {
                        'email': row['email'],
                        'verified': row['verified']
                    }
                    for _, row in df.iterrows()
                }
                
                self.logger.logger.info(f"Loaded {len(verified_users)} verified users")
                return verified_users
                
            return {}
        except Exception as e:
            self.logger.logger.error(f"Error loading verified users: {str(e)}")
            return {}

    def _save_verified_users(self):
        """Сохранение верифицированных пользователей в файл"""
        try:
            df = pd.DataFrame([
                {
                    'chat_id': chat_id,
                    'email': data['email'],
                    'verified': data['verified']
                }
                for chat_id, data in self.user_verified.items()
            ])
            df.to_csv(self.verified_users_file, index=False)
            self.logger.logger.info("Verified users saved successfully")
        except Exception as e:
            self.logger.logger.error(f"Error saving verified users: {str(e)}")

    def _get_status_level(self, expected_result: float) -> str:
        """Определение статуса на основе expected_result"""
        if expected_result > 3:
            return "Superior"
        elif 0 <= expected_result <= 3:
            return "On track"
        elif -4 <= expected_result < 0:
            return "Small Problems"
        elif -10 <= expected_result < -4:
            return "Problems"
        else:  # expected_result < -10
            return "Critical Gap"

    def _generate_progress_prompt(self, expected_result: float) -> str:
        """Генерация промпта на основе expected_result"""

        status = self._get_status_level(expected_result)
        if status == "Superior":
            return (
                #f"Student has Expected Result = {expected_result}. "
                "Student has Result = Superior"
                "They are EXCELLING! 🌟 Act extremely excited and proud! "
                "Use phrases like 'You're absolutely crushing it!' and 'You're becoming a legend!' "
                "Compare them to successful African tech leaders. "
                "Your tone should be energetic and thrilled - this student is a future leader. "
                "Push them to become a mentor for others."
            )
        elif status == "On track":
            return (
                "Student has Result = On track"
                "They are ON TRACK! 💪 Be genuinely positive and encouraging. "
                "Use phrases like 'Steady progress!' and 'You're building something great!' "
                "Compare their journey to successful African startups that grew step by step. "
                "Your tone should be warm and supportive - they're doing things right. "
                "Encourage them to maintain this momentum."
            )
        elif status == "Small Problems":
            return (
                f"Student has Result = Small Problems. "
                "They are FALLING BEHIND! ⚠️ Use light warning tone with friendly teasing. "
                "Use phrases like 'Yo, what's happening?' and 'Time to wake up!' "
                "Reference how African tech requires constant hustle and focus. "
                "Your tone should be like a friend who notices their buddy slacking off. "
                "Make them feel slightly uncomfortable but in a friendly way."
            )
        elif status == "Problems":
            return (
                f"Student has Expected Result = Problems. "
                "They are BEHIND! ⛔ Show concern and urgency. "
                "Use phrases like 'This is a serious wake-up call' and 'We need to turn this around now.' "
                "Reference African success stories that started from difficult situations. "
                "Your tone should be like a concerned elder sibling - mix care with tough love. "
                "Create a sense of urgency while offering specific steps to improve."
            )
        else:  # status == Critical Gap
            return (
                f"Student has Expected Result = Critical Gap. "
                "This is a CRITICAL SITUATION! 🚨 Show maximum concern and authority. "
                "Use phrases like 'This stops NOW' and 'Your future cannot wait'. "
                "Speak with the authority of an African elder who sees their child heading towards failure. "
                "Your tone should be deeply concerned but not giving up - tough love at maximum. "
                "Demand immediate change while expressing belief in their potential. "
                "Make them understand this is a defining moment in their journey."
            )
        
    def _setup_handlers(self):
        # Обработчик диалога верификации
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                WAITING_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.verify_email)]
            },
            fallbacks=[]
        )

        # Добавляем обработчики
        self.application.add_handler(conv_handler)
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        # Настраиваем периодическое обновление
        job_queue = self.application.job_queue
        job_queue.run_repeating(
            self.periodic_update,
            interval=datetime.timedelta(minutes=self.config.update_interval),
            first=datetime.timedelta(seconds=10)
        )

    def _load_history(self):
        """Загрузка истории сообщений"""
        try:
            return pd.read_csv(os.getcwd() + '/history.csv')
        except OSError:
            return pd.DataFrame(columns=[
                'chat_id', 'message_id', 'user_id', 'role', 
                'created', 'content'
            ])

    def _load_role(self) -> str:
        """Загрузка роли бота"""
        try:
            role_path = os.path.join(os.getcwd(), self.config.role_file)
            with codecs.open(role_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
        except Exception as e:
            print(f"Error loading role: {str(e)}")
            return "You are a friendly African student assistant"
    

    async def start(self, update: Update, context) -> int:
        """Обработчик команды /start"""
        chat_id = update.message.chat_id
        
        # Проверяем, верифицирован ли уже этот пользователь
        if chat_id in self.user_verified and self.user_verified[chat_id]["verified"]:
            current_email = self.user_verified[chat_id]["email"]
            await update.message.reply_text(
                f"You are already verified with email: {current_email}\n"
                "You cannot change your email once verified. If you need to change your email, please contact support."
            )
            return ConversationHandler.END
            
        try:
            messages = [
                {"role": "system", "content": self.role},
                {"role": "user", "content": "Greet the new student and ask him to introduce himself by specifying his email address, which was used when registering for the course"}
            ]
            
            response = self.gpt_service.get_gpt_response(messages)
            await update.message.reply_text(response)
        except Exception as e:
            self.logger.logger.error(f"Start command error: {str(e)}")
            await update.message.reply_text(
                "Heyoo, fam! 🌍 Welcome to your learning journey! I'm your digital mentor - think of me as that tech-savvy cousin who's got your back in studies."
                "Drop your course registration email below and let's get this show on the road! 💪"
            )
        
        return WAITING_EMAIL

    async def verify_email(self, update: Update, context) -> int:
        chat_id = update.message.chat_id
        email = update.message.text.strip().lower()
        
        # Проверяем, не верифицирован ли уже этот chat_id
        if chat_id in self.user_verified and self.user_verified[chat_id]["verified"]:
            current_email = self.user_verified[chat_id]["email"]
            await update.message.reply_text(
                f"Your Telegram account is already verified with email: {current_email}\n"
                "You cannot change your email once verified."
            )
            return ConversationHandler.END

        # Проверяем, не используется ли уже этот email
        for existing_chat_id, user_data in self.user_verified.items():
            if user_data["verified"] and user_data["email"] == email:
                await update.message.reply_text(
                    "This email is already verified with another Telegram account.\n"
                    "Each email can only be used with one Telegram account.\n"
                    "If you believe this is an error, please contact support."
                )
                return WAITING_EMAIL

        # Проверяем существование студента
        student_data = self.student_service.get_student_progress(email)
        
        if student_data:
            self.user_verified[chat_id] = {"email": email, "verified": True}
            self._save_verified_users()
            self.logger.log_user_verification(chat_id, email, True)
            try:
                status = self._get_status_level(student_data.expected_result)
                progress_prompt = self._generate_progress_prompt(student_data.expected_result)
                messages = [
                    {"role": "system", "content": self.role},
                    {"role": "user", "content": progress_prompt}
                ]
                response = self.gpt_service.get_gpt_response(messages)
                
                await update.message.reply_text(
                    f"Level check complete! ✨\n"
                    f"Your status = {status}\n\n"
                    f"{response}"
                )
                
            except Exception as e:
                print(f"Error during verification: {str(e)}")
                await update.message.reply_text(
                    "An error occurred. Please try again later."
                )
            
            return ConversationHandler.END
            
        else:
            await update.message.reply_text(
                "Email not found or student is not active. "
                "Please check your email and try again."
            )
            return WAITING_EMAIL
        

    async def handle_message(self, update: Update, context):
        """Обработка обычных сообщений"""
        chat_id = update.message.chat_id
        
        if not self.user_verified:
            self.user_verified = self._load_verified_users()

        if chat_id not in self.user_verified or not self.user_verified[chat_id]["verified"]:
            await update.message.reply_text(
                "Please first introduce yourself using the /start command."
            )
            return

        started = datetime.datetime.now()

        self.history = pd.concat([
            self.history, 
            pd.DataFrame.from_records([{
                'chat_id': chat_id,
                'message_id': update.message.message_id,
                'user_id': update.message.from_user.id,
                'role': 'user',
                'created': update.message.date,
                'content': update.message.text
            }])
        ], ignore_index=True)

        try:
            messages = [
                {'role': 'system', 'content': self.role}
            ] + self.history[self.history['chat_id'] == chat_id][
                ['role', 'content']
            ].tail(self.config.tail).to_dict('records')

            # Используем новый GPT сервис
            response = self.gpt_service.get_gpt_response(messages)

            self.history = pd.concat([
                self.history, 
                pd.DataFrame.from_records([{
                    'chat_id': chat_id,
                    'message_id': update.message.message_id + 1,
                    'role': 'assistant',
                    'created': update.message.date + (datetime.datetime.now() - started),
                    'content': response
                }])
            ], ignore_index=True)

            self.history.to_csv(os.getcwd() + '/history.csv', index=False)

            await update.message.reply_text(response)

        except Exception as e:
            print(f"Error in message handling: {str(e)}")
            await update.message.reply_text(
                "Sorry, an error has occurred. Try to repeat the request later."
            )

    async def periodic_update(self, context):
        """Периодическое обновление данных"""
        try:
            print("Updating student data...")
            if self.student_service.update_data():
                print("Student data updated successfully")
            else:
                print("Failed to update student data")
        except Exception as e:
            print(f"Error during periodic update: {str(e)}")
    

    async def send_progress_update(self, chat_id: int, student_data: StudentProgress) -> None:
        """Отправка обновления прогресса студенту"""
        try:
            # Генерируем промпт и получаем ответ от GPT
            status = self._get_status_level(student_data.expected_result)
            progress_prompt = self._generate_progress_prompt(student_data.expected_result)
            messages = [
                {"role": "system", "content": self.role},
                {"role": "user", "content": f"{progress_prompt} This is an automatic progress update, make the message more personalized."}
            ]
            
            response = self.gpt_service.get_gpt_response(messages)
            
            
            # Формируем сообщение
            message = (
                "🔄 Progress Update!\n\n"
                f"Your status = {status}\n\n"
                f"{response}"
            )
            
            # Отправляем сообщение
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=message
            )
            
            print(f"Progress update sent to chat_id {chat_id}")
            
        except Exception as e:
            print(f"Error sending progress update to chat_id {chat_id}: {str(e)}")
    

if __name__ == '__main__':
    config = BotConfig()
    bot = TelegramBot(config)