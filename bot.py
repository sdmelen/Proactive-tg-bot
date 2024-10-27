from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from telegram import Update
import openai as gpt
import pandas as pd
import os, codecs, datetime
from config.config import BotConfig
from modules.excel_handler import ExcelHandler
from modules.downloader import download_sheet

# Состояния диалога
WAITING_EMAIL = 1

class TelegramBot:
    def __init__(self, config: BotConfig):
        """
        Инициализация бота
        """
        self.config = config
        # Сначала загружаем актуальные данные
        self.update_sheet()
        self.excel_handler = ExcelHandler(config)
        gpt.api_key = config.gpt_key
        self.user_verified = {}
        self.history = self._load_history()
        self.role = self._load_role()

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
            print(f"Student found: {email}")
            self.user_verified[chat_id] = {"email": email, "verified": True}

            # Сохраняем сообщение пользователя в историю
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
                # Генерируем промпт и получаем ответ от GPT
                progress_prompt = self.excel_handler.generate_progress_prompt(student_data.delta_progress)
                messages = [
                    {"role": "system", "content": self.role},
                    {"role": "user", "content": progress_prompt}
                ]
                
                response = self.get_gpt_response(messages)

                # Сохраняем ответ в историю
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

                # Сохраняем историю в файл
                self.history.to_csv(os.getcwd() + '/history.csv', index=False)

                await update.message.reply_text(
                    f"Level check complete! ✨.\n"
                    f"Your Delta Progress score is showing: {student_data.delta_progress}\n\n"
                    f"Think of Delta Progress like a race with your classmates - positive numbers mean you're leading the pack,"
                    f"negative means you're behind the convoy. Time to know where you stand! 🏃‍♂️\n\n"
                    f"{response}"
                )

            except Exception as e:
                print(f"GPT Error during verification: {str(e)}")
                await update.message.reply_text(
                    f"Level check complete! ✨..\n"
                    f"Your Delta Progress score is showing: {student_data.delta_progress}\n\n"
                    "Let's work together on your progress!"
                    f"Think of Delta Progress like a race with your classmates - positive numbers mean you're leading the pack,"
                    f"negative means you're behind the convoy. Time to know where you stand! 🏃‍♂️\n\n"
                )

            return ConversationHandler.END

        else:
            print(f"Student not found: {email}")
            await update.message.reply_text(
                "I'm sorry, but I didn't find such an email in the list of students."
                "Please check the spelling and try again."
            )
            return WAITING_EMAIL

    async def handle_message(self, update: Update, context):
        """Обработка обычных сообщений после верификации"""
        chat_id = update.message.chat_id
        
        if chat_id not in self.user_verified or not self.user_verified[chat_id]["verified"]:
            await update.message.reply_text(
                "Please first introduce yourself using the /start command, "
                "specifying your email address."
            )
            return

        started = datetime.datetime.now()

        # Сохраняем сообщение пользователя
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
            # Подготовка сообщений для GPT
            messages = [
                {'role': 'system', 'content': self.role}
            ] + self.history[self.history['chat_id'] == chat_id][
                ['role', 'content']
            ].tail(self.config.tail).to_dict('records')

            response = self.get_gpt_response(messages)

            # Сохраняем ответ в историю
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

            # Сохраняем историю в файл
            self.history.to_csv(os.getcwd() + '/history.csv', index=False)

            await update.message.reply_text(response)

        except Exception as e:
            print(f"Error in message handling: {str(e)}")
            await update.message.reply_text(
                "Sorry, an error has occurred. Try to repeat the request later."
            )

    async def periodic_update(self, context):
        """
        Периодическое обновление данных
        """
        try:
            # Обновляем таблицу
            self.update_sheet()
            # Обновляем данные в ExcelHandler
            await self.excel_handler.update_data()
            print(f"Scheduled update completed at {datetime.datetime.now()}")
        except Exception as e:
            print(f"Error in periodic update: {str(e)}")

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
            interval=datetime.timedelta(hours=24),
            first=datetime.timedelta(seconds=0)  # Первый запуск сразу
        )

        print('Запуск бота...')
        application.run_polling(1.0)

if __name__ == '__main__':
    config = BotConfig(
        bot_key='',
        gpt_key='',
        excel_file_path='C:/Users/HUAWEI/Desktop/py/Proactive-tg-bot/Аналитика.xlsx',
        role_file='role.txt',
        model="gpt-4o-mini",
        temperature=0.5,
        tail=6
    )
    
    bot = TelegramBot(config)
    bot.run()