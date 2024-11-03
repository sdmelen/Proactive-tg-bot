import requests
from typing import List, Dict, Any
from config.config import BotConfig

class GPTService:
    def __init__(self, config: BotConfig):
        self.config = config
        self.headers = {
            'Authorization': f"Bearer {config.gpt_key}"
        }

    def get_gpt_response(self, messages: List[Dict[str, str]], temperature: float = None) -> str:
        """
        Получение ответа от GPT через прокси-сервер
        """
        try:
            temp = temperature if temperature is not None else self.config.temperature
            
            data = {
                'messages': messages,
                'model': self.config.model,
                'temperature': temp,
            }
            
            response = requests.post(
                url=f'{self.config.openai_proxy_host}get-gpt-answer/',
                json=data,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200 and response.json().get('success'):
                return response.json().get('answer')
            else:
                print(f'Ошибка при запросе к GPT прокси: {response.status_code}, {response.text}')
                raise Exception(f'Неудачный запрос к GPT! STATUS_CODE: {response.status_code}')
                
        except Exception as e:
            print(f"GPT Error: {str(e)}")
            raise