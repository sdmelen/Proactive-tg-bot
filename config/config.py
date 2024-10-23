from dataclasses import dataclass

@dataclass
class BotConfig:
    bot_key: str
    gpt_key: str
    excel_file_path: str
    tail: int = 6
    model: str = "gpt-4o-mini"
    temperature: float = 0.5
    history_file: str = 'history.csv'
    role_file: str = 'role.txt'
    update_interval: int = 24  # часы
    excel_file_path: str = "C:/Users/HUAWEI/Desktop/py/Proactive-tg-bot/Аналитика.xlsx"