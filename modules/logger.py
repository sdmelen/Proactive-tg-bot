import logging
import logging.handlers
import os
from datetime import datetime
from typing import Optional

class BotLogger:
    def __init__(self, log_directory: str = "logs"):
        self.log_directory = log_directory
        self._setup_directory()
        self.logger = self._configure_logger()

    def _setup_directory(self) -> None:
        """Создание директории для логов если она не существует"""
        if not os.path.exists(self.log_directory):
            os.makedirs(self.log_directory)

    def _configure_logger(self) -> logging.Logger:
        """Настройка логгера с разделением по уровням логирования"""
        logger = logging.getLogger('AumitEduBot')
        logger.setLevel(logging.DEBUG)

        # Формат логов
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Обработчик для всех логов
        all_handler = logging.handlers.RotatingFileHandler(
            filename=os.path.join(self.log_directory, 'all.log'),
            maxBytes=5*1024*1024,  # 5MB
            backupCount=5,
            encoding='utf-8'
        )
        all_handler.setLevel(logging.DEBUG)
        all_handler.setFormatter(formatter)

        # Обработчик для ошибок
        error_handler = logging.handlers.RotatingFileHandler(
            filename=os.path.join(self.log_directory, 'error.log'),
            maxBytes=5*1024*1024,  # 5MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)

        # Консольный обработчик
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        # Добавляем обработчики к логгеру
        logger.addHandler(all_handler)
        logger.addHandler(error_handler)
        logger.addHandler(console_handler)

        return logger

    def log_bot_startup(self, config: dict) -> None:
        """Логирование запуска бота"""
        self.logger.info("Bot starting up with configuration:")
        for key, value in config.items():
            if 'key' in key.lower() or 'token' in key.lower():
                self.logger.info(f"{key}: ***hidden***")
            else:
                self.logger.info(f"{key}: {value}")

    def log_user_verification(self, chat_id: int, email: str, success: bool) -> None:
        """Логирование процесса верификации пользователя"""
        if success:
            self.logger.info(f"User verification successful - Chat ID: {chat_id}, Email: {email}")
        else:
            self.logger.warning(f"User verification failed - Chat ID: {chat_id}, Email: {email}")

    def log_api_request(self, endpoint: str, status_code: Optional[int] = None, error: Optional[str] = None) -> None:
        """Логирование API запросов"""
        if status_code == 200:
            self.logger.info(f"API request successful - Endpoint: {endpoint}")
        else:
            self.logger.error(f"API request failed - Endpoint: {endpoint}, Status: {status_code}, Error: {error}")

    def log_gpt_interaction(self, chat_id: int, success: bool, error: Optional[str] = None) -> None:
        """Логирование взаимодействий с GPT"""
        if success:
            self.logger.info(f"GPT interaction successful - Chat ID: {chat_id}")
        else:
            self.logger.error(f"GPT interaction failed - Chat ID: {chat_id}, Error: {error}")

    def log_student_update(self, email: str, expected_result: float) -> None:
        """Логирование обновления данных студента"""
        self.logger.info(f"Student progress updated - Email: {email}, Expected Result: {expected_result}")