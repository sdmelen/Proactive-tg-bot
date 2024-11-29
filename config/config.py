import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class BotConfig:
    bot_key: str = os.getenv('BOT_TOKEN')
    gpt_key: str = os.getenv('GPT_KEY')
    openai_proxy_host: str = os.getenv('OPENAI_PROXY_HOST')

    tail: int = 6
    model: str = "gpt-4o-mini"
    temperature: float = 0.5
    history_file: str = 'history.csv'
    role_file: str = 'role.txt'
    update_interval: int = 10 #в минутах
    
    log_directory: str = "logs"
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')
    max_log_size: int = 5 * 1024 * 1024  # 5MB
    backup_count: int = 5