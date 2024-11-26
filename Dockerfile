FROM python:3.11-alpine

WORKDIR /app

COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .

# Run the bot
CMD ["python", "bot.py"]
