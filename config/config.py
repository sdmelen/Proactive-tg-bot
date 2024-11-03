import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class BotConfig:
    bot_key: str = os.getenv('BOT_TOKEN')
    gpt_key: str = os.getenv('GPT_KEY')
    excel_file_path: str = os.getenv('EXCEL_FILE_PATH')
    openai_proxy_host: str = os.getenv('OPENAI_PROXY_HOST') 
    tail: int = 6
    model: str = "gpt-4o-mini"
    temperature: float = 0.5
    history_file: str = 'history.csv'
    role_file: str = 'role.txt'
    update_interval: int = 1  #в часах

    def __post_init__(self):
        """Проверка наличия обязательных переменных окружения"""
        required_vars = {
            'BOT_TOKEN': self.bot_key,
            'GPT_KEY': self.gpt_key,
            'OPENAI_PROXY_HOST': self.openai_proxy_host,
            'EXCEL_FILE_PATH': self.excel_file_path
        }
        
        missing_vars = [var for var, value in required_vars.items() if not value]
        
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}\n"
                f"Please check your .env file"
            )