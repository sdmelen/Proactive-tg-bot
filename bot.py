from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from telegram import Update
import openai as gpt
import pandas as pd
import os, codecs, datetime
from config.config import BotConfig
from modules.excel_handler import ExcelHandler

# Состояния диалога
WAITING_NAME = 1

class TelegramBot:
    def __init__(self, config: BotConfig):
        """
        Инициализация бота
        """
        self.config = config
        self.excel_handler = ExcelHandler(config)
        gpt.api_key = config.gpt_key
        self.user_verified = {}
        self.history = self._load_history()
        self.role = self._load_role()

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
            return "Ты - дружелюбный помощник для студентов."

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
                {"role": "user", "content": "Поприветствуй нового студента и попроси его представиться"}
            ]
            
            response = self.get_gpt_response(messages)
            await update.message.reply_text(response)
        except Exception as e:
            print(f"Start command error: {str(e)}")
            await update.message.reply_text(
                "Привет! Я твой помощник в обучении. Пожалуйста, представься - "
                "напиши свои имя и фамилию как в списке группы."
            )
        
        return WAITING_NAME

    async def verify_name(self, update: Update, context) -> int:
        """Проверка имени студента"""
        chat_id = update.message.chat_id
        full_name = update.message.text.strip()
        started = datetime.datetime.now()

        print(f"Verifying name: {full_name}")
        student_data = self.excel_handler.get_student_progress(full_name)

        if student_data:
            print(f"Student found: {full_name}")
            self.user_verified[chat_id] = {"name": full_name, "verified": True}

            # Сохраняем сообщение пользователя в историю
            self.history = pd.concat([
                self.history, 
                pd.DataFrame.from_records([{
                    'chat_id': chat_id,
                    'message_id': update.message.message_id,
                    'user_id': update.message.from_user.id,
                    'role': 'user',
                    'created': update.message.date,
                    'content': full_name
                }])
            ], ignore_index=True)

            try:
                # Генерируем промпт и получаем ответ от GPT
                progress_prompt = self.excel_handler.generate_progress_prompt(student_data.progress)
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
                    f"Отлично! Я нашел тебя в базе.\n"
                    f"Твой текущий прогресс: {student_data.progress}%\n\n"
                    f"{response}"
                )

            except Exception as e:
                print(f"GPT Error during verification: {str(e)}")
                await update.message.reply_text(
                    f"Отлично! Я нашел тебя в базе.\n"
                    f"Твой текущий прогресс: {student_data.progress}%\n\n"
                    "Продолжай в том же духе! Я здесь, чтобы помочь тебе в обучении."
                )

            return ConversationHandler.END

        else:
            print(f"Student not found: {full_name}")
            await update.message.reply_text(
                "Извини, но я не нашел такого имени в списке студентов. "
                "Пожалуйста, проверь правильность написания и попробуй еще раз."
            )
            return WAITING_NAME

    async def handle_message(self, update: Update, context):
        """Обработка обычных сообщений после верификации"""
        chat_id = update.message.chat_id
        
        if chat_id not in self.user_verified or not self.user_verified[chat_id]["verified"]:
            await update.message.reply_text(
                "Пожалуйста, сначала представьтесь с помощью команды /start"
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
                "Извините, произошла ошибка. Попробуйте повторить запрос позже."
            )

    def run(self):
        """Запуск бота"""
        application = Application.builder().token(self.config.bot_key).build()

        # Обработчик диалога верификации
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                WAITING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.verify_name)]
            },
            fallbacks=[]
        )

        # Добавляем обработчики
        application.add_handler(conv_handler)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        # Запускаем бота
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