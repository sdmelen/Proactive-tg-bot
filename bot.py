from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from telegram import Update
import openai as gpt
import pandas as pd
import os, codecs, datetime
from config.config import BotConfig
from modules.excel_handler import ExcelHandler, StudentData
from modules.downloader import download_sheet
from modules.gpt_service import GPTService

# Состояния диалога
WAITING_EMAIL = 1

class TelegramBot:
    def __init__(self, config: BotConfig):
        """
        Инициализация бота
        """
        self.config = config
        self.application = Application.builder().token(self.config.bot_key).build()
        
        # Инициализация сервисов
        self.update_sheet()
        self.excel_handler = ExcelHandler(config)
        self.gpt_service = GPTService(config)  # Добавляем GPT сервис
        self.user_verified = {}
        self.history = self._load_history()
        self.role = self._load_role()
        self._setup_handlers()
        
    def _setup_handlers(self):
        """
        Настройка обработчиков команд и сообщений
        """
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

    def update_sheet(self):
        """
        Обновление Excel файла из Google Sheets
        """
        try:
            print("Updating data from Google Sheets...")
            download_sheet()
            print("Data update completed successfully")
        except Exception as e:
            print(f"Error updating data: {str(e)}")

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

    def get_gpt_response(self, messages: list) -> str:
        """
        Получение ответа от OpenAI GPT (синхронная версия)
        """
        try:
            response = gpt.ChatCompletion.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature
            )
            return response['choices'][0]['message']['content']
        except Exception as e:
            print(f"GPT Error: {str(e)}")
            raise

    async def start(self, update: Update, context) -> int:
        """Обработчик команды /start"""
        try:
            messages = [
                {"role": "system", "content": self.role},
                {"role": "user", "content": "Greet the new student and ask him to introduce himself by specifying his email address, which was used when registering for the course"}
            ]
            
            response = self.get_gpt_response(messages)
            await update.message.reply_text(response)
        except Exception as e:
            print(f"Start command error: {str(e)}")
            await update.message.reply_text(
                "Heyoo, fam! 🌍 Welcome to your learning journey! I'm your digital mentor - think of me as that tech-savvy cousin who's got your back in studies."
                "Drop your course registration email below and let's get this show on the road! 💪"
            )
        
        return WAITING_EMAIL

    async def verify_email(self, update: Update, context) -> int:
        """Проверка email студента"""
        chat_id = update.message.chat_id
        email = update.message.text.strip()
        started = datetime.datetime.now()

        print(f"Verifying email: {email}")
        student_data = self.excel_handler.get_student_progress(email)

        if student_data:
            self.user_verified[chat_id] = {"email": email, "verified": True}

            self.history = pd.concat([
                self.history, 
                pd.DataFrame.from_records([{
                    'chat_id': chat_id,
                    'message_id': update.message.message_id,
                    'user_id': update.message.from_user.id,
                    'role': 'user',
                    'created': update.message.date,
                    'content': email
                }])
            ], ignore_index=True)

            try:
                # Используем новый GPT сервис
                progress_prompt = self.excel_handler.generate_progress_prompt(student_data.delta_progress)
                messages = [
                    {"role": "system", "content": self.role},
                    {"role": "user", "content": progress_prompt}
                ]
                
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

                await update.message.reply_text(
                    f"Level check complete! ✨\n"
                    f"Your Delta Progress score is showing: {student_data.delta_progress}\n\n"
                    f"Think of Delta Progress like a race with your classmates - positive numbers mean you're leading the pack,"
                    f"negative means you're behind the convoy. Time to know where you stand! 🏃‍♂️\n\n"
                    f"{response}"
                )

            except Exception as e:
                print(f"GPT Error during verification: {str(e)}")
                await update.message.reply_text(
                    f"Level check complete! ✨\n"
                    f"Your Delta Progress score is showing: {student_data.delta_progress}\n\n"
                    "Let's work together on your progress!"
                )

            return ConversationHandler.END
        else:
            await update.message.reply_text(
                "I'm sorry, but I didn't find such an email in the list of students. "
                "Please check the spelling and try again."
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
        """
        Периодическое обновление данных и отправка обновлений студентам
        """
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"\n[{current_time}] Запуск периодического обновления...")
        
        try:
            # Сохраняем предыдущие данные для сравнения
            previous_data = self.excel_handler.students_data.copy()
            
            # Обновляем данные
            print(f"[{current_time}] Загрузка новых данных...")
            self.update_sheet()
            await self.excel_handler.update_data()
            
            print(f"Верифицированные пользователи: {self.user_verified}")
            
            # Проходим по всем верифицированным пользователям
            for chat_id, user_data in self.user_verified.items():
                if user_data["verified"]:
                    email = user_data["email"]
                    print(f"Проверка обновлений для {email}")
                    student_data = self.excel_handler.get_student_progress(email)
                    
                    if student_data:
                        # Проверяем, изменился ли прогресс
                        previous_progress = (
                            previous_data[email].delta_progress 
                            if email in previous_data 
                            else None
                        )
                        
                        current_progress = student_data.delta_progress
                        print(f"Previous progress: {previous_progress}")
                        print(f"Current progress: {current_progress}")
                        
                        if (previous_progress is None or 
                            abs(current_progress - previous_progress) >= 0.01):  # учитываем небольшую погрешность
                            print(f"[{current_time}] Отправка обновления для {email}")
                            await self.send_progress_update(chat_id, student_data)
                        else:
                            print(f"[{current_time}] Прогресс не изменился для {email}")
                    else:
                        print(f"[{current_time}] Не найдены данные для {email}")
            
            print(f"[{current_time}] Периодическое обновление завершено")
            
        except Exception as e:
            print(f"[{current_time}] Ошибка при периодическом обновлении: {str(e)}")
            import traceback
            print("Full error traceback:")
            print(traceback.format_exc())
    

    async def send_progress_update(self, chat_id: int, student_data: StudentData) -> None:
        """
        Отправка обновления прогресса студенту
        """
        try:
            # Генерируем промпт и получаем ответ от GPT
            progress_prompt = self.excel_handler.generate_progress_prompt(student_data.delta_progress)
            messages = [
                {"role": "system", "content": self.role},
                {"role": "user", "content": f"{progress_prompt} This is an automatic progress update, make the message more personalized."}
            ]
            
            response = self.get_gpt_response(messages)
            
            # Формируем сообщение
            message = (
                "🔄 Progress Update!\n\n"
                f"Your current Delta Progress: {student_data.delta_progress}\n\n"
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
            # Добавляем более подробное логирование
            import traceback
            print("Full error traceback:")
            print(traceback.format_exc())
    
    def run(self):
        """Запуск бота"""
        application = Application.builder().token(self.config.bot_key).build()

        # Обработчик диалога верификации
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                WAITING_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.verify_email)]
            },
            fallbacks=[]
        )

        # Добавляем обработчики
        application.add_handler(conv_handler)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        # Настраиваем периодическое обновление данных
        job_queue = application.job_queue
        # Запускаем обновление каждые 24 часа
        job_queue.run_repeating(
            self.periodic_update,
            interval=datetime.timedelta(minutes=self.config.update_interval),
            first=datetime.timedelta(seconds=0)  # Первый запуск сразу
        )

        print('Запуск бота...')
        print(f'Настроено обновление данных каждую {self.config.update_interval} минуту')
        application.run_polling(1.0)

if __name__ == '__main__':
    config = BotConfig()
    bot = TelegramBot(config)
    bot.run()