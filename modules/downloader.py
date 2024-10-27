import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os

def download_sheet():
    """
    Загрузка данных из Google Sheets и сохранение в Excel
    Returns:
        bool: True если загрузка успешна, False в случае ошибки
    """
    # Определяем области доступа
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    # ID таблицы можно взять из URL между /d/ и /edit
    SPREADSHEET_ID = '1X26rO7AhzJqJwbfUDshoGKFQLDjrXriJnSz9FcflDhY'

    try:
        # Подключаем учетные данные
        credentials = Credentials.from_service_account_file(
            'service_account.json',
            scopes=scope
        )
        
        # Авторизуемся и получаем доступ к таблице
        client = gspread.authorize(credentials)
        
        # Открываем таблицу по ID и берем первый лист
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        
        # Получаем все значения (включая заголовки)
        all_values = sheet.get_all_values()
        
        if len(all_values) > 0:
            # Создаем DataFrame, используя первую строку как заголовки
            df = pd.DataFrame(all_values[1:], columns=all_values[0])
            
            # Сохраняем в Excel
            df.to_excel('Аналитика.xlsx', index=False)
            return True
        else:
            print("Таблица пуста!")
            return False

    except Exception as e:
        print(f"Произошла ошибка при загрузке данных: {str(e)}")
        return False

# Если файл запущен напрямую
if __name__ == "__main__":
    download_sheet()