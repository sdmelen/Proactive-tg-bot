from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from telegram import Update
import pandas as pd
import os, codecs, datetime
from config.config import BotConfig
from modules.student_data_service import StudentDataService, StudentProgress
from modules.gpt_service import GPTService

# Состояния диалога
WAITING_EMAIL = 1

class TelegramBot:
    def __init__(self, config: BotConfig):
        # Инициализация бота
        self.config = config
        self.application = Application.builder().token(self.config.bot_key).build()
        
        # Инициализация сервисов
        self.student_service = StudentDataService()
        self.gpt_service = GPTService(config)  # Добавляем GPT сервис
        self.user_verified = {}
        self.history = self._load_history()
        self.role = self._load_role()
        self._setup_handlers()
        print('Запуск бота...')
        print(f'Настроено обновление данных каждую {self.config.update_interval} минуту')
        self.application.run_polling(1.0)
    
    def _generate_progress_prompt(self, expected_result: float) -> str:
        """Генерация промпта на основе expected_result"""
        if expected_result > 3:
            return (
                f"Student has Expected Result = {expected_result}. "
                "Give praise using local expressions of excellence. "
                "Challenge them to lift others as they rise. "
                "Emphasize their role in community success."
            )
        elif 0 <= expected_result <= 3:
            return (
                f"Student has Expected Result = {expected_result}. "
                "Acknowledge their steady progress with familiar encouragement. "
                "Use local success stories as motivation. "
                "Keep the energy positive and communal."
            )
        elif -4 <= expected_result < 0:
            return (
                f"Student has Expected Result = {expected_result}. "
                "Use playful local banter to highlight issues. "
                "Mix street-smart wisdom with academic advice. "
                "Provide guidance with cultural context."
            )
        elif -10 <= expected_result < -4:
            return (
                f"Student has Expected Result = {expected_result}. "
                "Get serious but maintain hope and brotherhood/sisterhood. "
                "Draw parallels to local success stories who overcame challenges. "
                "Push for immediate action with community support."
            )
        else:  # expected_result < -10
            return (
                f"Student has Expected Result = {expected_result}. "
                "Show tough love like a concerned family member. "
                "Express disappointment while affirming potential. "
                "Demand action with cultural resonance."
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
        try:
            messages = [
                {"role": "system", "content": self.role},
                {"role": "user", "content": "Greet the new student and ask him to introduce himself by specifying his email address, which was used when registering for the course"}
            ]
            
            response = self.gpt_service.get_gpt_response(messages)
            await update.message.reply_text(response)
        except Exception as e:
            print(f"Start command error: {str(e)}")
            await update.message.reply_text(
                "Heyoo, fam! 🌍 Welcome to your learning journey! I'm your digital mentor - think of me as that tech-savvy cousin who's got your back in studies."
                "Drop your course registration email below and let's get this show on the road! 💪"
            )
        
        return WAITING_EMAIL

    async def verify_email(self, update: Update, context) -> int:
        chat_id = update.message.chat_id
        email = update.message.text.strip()
        
        # Используем новый сервис для проверки студента
        student_data = self.student_service.get_student_progress(email)
        
        if student_data:
            self.user_verified[chat_id] = {"email": email, "verified": True}
            
            try:
                # Генерируем промпт на основе expected_result вместо delta_progress
                progress_prompt = self._generate_progress_prompt(student_data.expected_result)
                messages = [
                    {"role": "system", "content": self.role},
                    {"role": "user", "content": progress_prompt}
                ]
                
                response = self.gpt_service.get_gpt_response(messages)
                
                await update.message.reply_text(
                    f"Level check complete! ✨\n"
                    f"Your Progress: {student_data.progress}%\n"
                    f"Expected Result: {student_data.expected_result}\n\n"
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
            progress_prompt = self._generate_progress_prompt(student_data.expected_result)
            messages = [
                {"role": "system", "content": self.role},
                {"role": "user", "content": f"{progress_prompt} This is an automatic progress update, make the message more personalized."}
            ]
            
            response = self.gpt_service.get_gpt_response(messages)
            
            # Формируем сообщение
            message = (
                "🔄 Progress Update!\n\n"
                f"Your current Progress: {student_data.progress}%\n"
                f"Expected Result: {student_data.expected_result}\n\n"
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
            import traceback
            print("Full error traceback:")
            print(traceback.format_exc())
    

if __name__ == '__main__':
    config = BotConfig()
    bot = TelegramBot(config)