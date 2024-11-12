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
    aumit_username: str = os.getenv('AUMIT_USERNAME')
    aumit_password: str = os.getenv('AUMIT_PASSWORD')

    tail: int = 6
    model: str = "gpt-4o-mini"
    temperature: float = 0.5
    history_file: str = 'history.csv'
    role_file: str = 'role.txt'
    update_interval: int = 5 #в минутах