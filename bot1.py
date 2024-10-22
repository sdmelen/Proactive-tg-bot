from telegram.ext import *
import openai as gpt
import pandas as pd
import os, codecs, datetime
from telegram import Bot
import asyncio

# Ключи бота, GPT и другие настройки Ключи вставьте ваши, эти ключи для образца
bot_key = 'Вставьте сюда свой tg - API ключ'  # API AUMIT tg бота
gpt_key = 'Вставьте сюда свой Open AI API ключ '  # API ключ OpenAI GPT

# Параметры GPT
tail = 6  # Длина истории диалога (количество последних сообщений)
model = "gpt-4o-mini"  # Модель нейросети GPT
temperature = 0.5  # Температура (определяет степень "креативности" модели)

# Инициализация бота
bot = Bot(token=bot_key)

# Загрузка истории сообщений из файла или создание нового датафрейма, если файл не существует
try:
    history = pd.read_csv(os.getcwd() + '/history.csv')
except OSError:
    # Если файл не существует, создается пустая таблица
    history = pd.DataFrame(columns=['chat_id', 'message_id', 'user_id', 'role', 'created', 'content'])

# Установка ключа API для OpenAI GPT
gpt.api_key = gpt_key

print('Запуск бота...')

################       КОМАНДА /start  ###############################
async def start(update, context):
    """
    Функция, обрабатывающая команду /start.
    Отправляет приветственное сообщение пользователю.
    """
    await update.message.reply_text('Hello wanderer, I hope you are ready to be stunned by secret knowledge today')

#####################    ОСНОВНАЯ ФУНКЦИЯ     ####################################
async def ask(update, context):
    """
    Основная функция для обработки сообщений пользователя.
    Получает запрос от пользователя, передает его в GPT, и возвращает ответ.
    """
    global history  # Глобальная переменная для хранения истории сообщений

    # Фиксируем время начала обработки запроса
    started = datetime.datetime.now()

    # Запись входящего сообщения пользователя в историю
    history = pd.concat([history, pd.DataFrame.from_records([{
        'chat_id': update.message.chat_id,
        'message_id': update.message.message_id,
        'user_id': update.message.from_user.id,
        'role': 'user',
        'created': update.message.date,
        'content': update.message.text
    }])], ignore_index=True)

    # Чтение роли из файла (если роль бота задается в отдельном файле)
    role_file = os.getcwd() + '/role.txt'
    with codecs.open(role_file, 'r', encoding='utf-8') as file:
        role = file.read()

    try:
        # Подготовка сообщений для GPT: роль бота + последние сообщения из истории диалога
        messages = [{'role': 'system', 'content': role},
                    {'role': 'user', 'content': ''}] + history[history['chat_id'] == update.message.chat_id][
                        ['role', 'content']].tail(tail).to_dict('records')

        # Запрос к GPT для получения ответа
        response = gpt.ChatCompletion.create(model=model, temperature=temperature, messages=messages)

    except Exception as e:
        # В случае ошибки отправляем сообщение пользователю
        await update.message.reply_text('Что-то пошло не так. Попробуйте позже.')
        return

    # Извлечение ответа от GPT
    otvet = response['choices'][0]['message']['content']

    # Запись ответа GPT в историю сообщений
    history = pd.concat([history, pd.DataFrame.from_records([{
        'chat_id': update.message.chat_id,
        'message_id': update.message.message_id + 1,
        'role': 'assistant',
        'created': update.message.date + (datetime.datetime.now() - started),
        'content': otvet
    }])], ignore_index=True)

    # Сохранение истории сообщений в файл
    history.to_csv(os.getcwd() + '/history.csv', index=False)

    # Отправка ответа пользователю
    await update.message.reply_text(otvet)

##################  КОНЕЦ ОСНОВНОЙ ФУНКЦИИ   ####################################

# Запуск бота
if __name__ == '__main__':
    # Создание и настройка приложения Telegram Bot API
    application = Application.builder().token(bot_key).build()

    # Добавление команды /start и обработчика сообщений
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ask))

    # Запуск бота с polling (постоянный опрос сервера Telegram)
    application.run_polling(1.0)