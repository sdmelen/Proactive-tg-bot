import requests
from typing import List, Dict, Any
from config.config import BotConfig
from .logger import BotLogger

class GPTService:
    def __init__(self, config: BotConfig, logger: BotLogger):
        self.config = config
        self.headers = {'Authorization': f"Bearer {config.gpt_key}"}
        self.logger = logger

    def get_gpt_response(self, messages: List[Dict[str, str]], temperature: float = None) -> str:
        try:
            self.logger.logger.debug("Preparing GPT request")
            temp = temperature if temperature is not None else self.config.temperature
            
            data = {
                'messages': messages,
                'model': self.config.model,
                'temperature': temp,
            }
            
            self.logger.logger.debug(f"Sending request to GPT proxy: {self.config.openai_proxy_host}")
            
            response = requests.post(
                url=f'{self.config.openai_proxy_host}get-gpt-answer/',
                json=data,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200 and response.json().get('success'):
                self.logger.logger.info("Successfully received GPT response")
                return response.json().get('answer')
            else:
                error_msg = f'GPT proxy error: {response.status_code}, {response.text}'
                self.logger.logger.error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            self.logger.logger.error(f"GPT Error: {str(e)}", exc_info=True)
            raise