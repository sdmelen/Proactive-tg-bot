from telegram.ext import *
import openai as gpt
import pandas as pd
import os, codecs, datetime
from telegram import Bot
import asyncio
from typing import List, Dict, Any  # Добавляем типизацию для лучшей читаемости
from dataclasses import dataclass  # Для создания конфигурационного класса

# Создаем класс для конфигурации бота
@dataclass
class BotConfig:
    bot_key: str
    gpt_key: str
    tail: int = 6
    model: str = "gpt-4o-mini"
    temperature: float = 0.5
    history_file: str = 'history.csv'
    role_file: str = 'role.txt'

class TelegramBot:
    def __init__(self, config: BotConfig):
        """
        Инициализация бота с конфигурацией
        """
        self.config = config
        self.bot = Bot(token=config.bot_key)
        self.history = self._load_history()
        gpt.api_key = config.gpt_key

    def _load_history(self) -> pd.DataFrame:
        """
        Загрузка истории сообщений из файла
        Returns:
            pd.DataFrame: DataFrame с историей сообщений
        """
        try:
            return pd.read_csv(os.path.join(os.getcwd(), self.config.history_file))
        except OSError:
            return pd.DataFrame(columns=[
                'chat_id', 'message_id', 'user_id', 'role', 
                'created', 'content'
            ])

    def _load_role(self) -> str:
        """
        Загрузка роли бота из файла
        Returns:
            str: Содержимое файла роли
        """
        role_path = os.path.join(os.getcwd(), self.config.role_file)
        with codecs.open(role_path, 'r', encoding='utf-8') as file:
            return file.read()

    def _prepare_messages(self, chat_id: int, tail: int) -> List[Dict[str, str]]:
        """
        Подготовка сообщений для отправки в GPT
        Args:
            chat_id: ID чата
            tail: Количество последних сообщений
        Returns:
            List[Dict[str, str]]: Подготовленные сообщения
        """
        role = self._load_role()
        base_messages = [
            {'role': 'system', 'content': role},
            {'role': 'user', 'content': ''}
        ]
        
        history_messages = self.history[
            self.history['chat_id'] == chat_id
        ][['role', 'content']].tail(tail).to_dict('records')
        
        return base_messages + history_messages

    def _add_to_history(self, message_data: Dict[str, Any]) -> None:
        """
        Добавление нового сообщения в историю
        Args:
            message_data: Данные сообщения
        """
        self.history = pd.concat([
            self.history, 
            pd.DataFrame.from_records([message_data])
        ], ignore_index=True)
        self.history.to_csv(
            os.path.join(os.getcwd(), self.config.history_file), 
            index=False
        )

    async def start(self, update: Any, context: Any) -> None:
        """
        Обработчик команды /start
        """
        await update.message.reply_text(
            'Hello wanderer, I hope you are ready to be stunned by secret knowledge today'
        )

    async def ask(self, update: Any, context: Any) -> None:
        """
        Основной обработчик сообщений
        """
        started = datetime.datetime.now()

        # Сохраняем сообщение пользователя
        user_message = {
            'chat_id': update.message.chat_id,
            'message_id': update.message.message_id,
            'user_id': update.message.from_user.id,
            'role': 'user',
            'created': update.message.date,
            'content': update.message.text
        }
        self._add_to_history(user_message)

        try:
            messages = self._prepare_messages(
                update.message.chat_id, 
                self.config.tail
            )
            
            response = gpt.ChatCompletion.create(
                model=self.config.model,
                temperature=self.config.temperature,
                messages=messages
            )
            
            otvet = response['choices'][0]['message']['content']

            # Сохраняем ответ ассистента
            assistant_message = {
                'chat_id': update.message.chat_id,
                'message_id': update.message.message_id + 1,
                'role': 'assistant',
                'created': update.message.date + (datetime.datetime.now() - started),
                'content': otvet
            }
            self._add_to_history(assistant_message)

            await update.message.reply_text(otvet)

        except Exception as e:
            await update.message.reply_text('Что-то пошло не так. Попробуйте позже.')
            # В будущем здесь можно добавить логирование ошибок
            print(f"Error occurred: {str(e)}")

    def run(self) -> None:
        """
        Запуск бота
        """
        application = Application.builder().token(self.config.bot_key).build()
        application.add_handler(CommandHandler('start', self.start))
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.ask)
        )
        application.run_polling(1.0)

if __name__ == '__main__':
    # Конфигурация бота
    config = BotConfig(
        bot_key='',
        gpt_key=''
    )
    
    # Создание и запуск бота
    bot = TelegramBot(config)
    print('Запуск бота...')
    bot.run()