import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
from dotenv import load_dotenv

load_dotenv()

@dataclass
class StudentProgress:
    email: str
    start_date: Optional[str]
    end_date: Optional[str]
    progress: float
    expected_result: float
    course_id: str

class StudentDataService:
    def __init__(self):
        self.login_url = "https://aumit.us/login-page-um/"
        self.data_url = "https://aumit.us/studresult/"
        self.username = os.getenv('AUMIT_USERNAME')
        self.password = os.getenv('AUMIT_PASSWORD')
        self.students_data: Dict[str, StudentProgress] = {}

    def update_data(self) -> bool:
        """Обновление данных студентов"""
        try:
            #Опции Chrome
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # Запуск браузера в фоновом режиме
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])  # Отключение логов DevTools
            
            # Инициализация драйвера с опциями
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(
                service=service,
                options=chrome_options
            )

            try:
                # Логин
                driver.get(self.login_url)
                driver.find_element(By.ID, "username-1098").send_keys(self.username)
                driver.find_element(By.ID, "user_password-1098").send_keys(self.password)
                driver.find_element(By.ID, "um-submit-btn").click()
                time.sleep(5)

                # Получение данных
                driver.get(self.data_url)
                time.sleep(3)
                page_source = driver.page_source

                # Парсинг данных
                self._parse_data(page_source)
                return True

            finally:
                driver.quit()

        except Exception as e:
            print(f"Error updating student data: {str(e)}")
            return False

    def _parse_data(self, page_source: str):
        """Парсинг HTML и обновление данных студентов"""
        soup = BeautifulSoup(page_source, 'html.parser')
        tables = soup.find_all("div", {"class": "lp-student-progress-table"})
        
        # Очищаем текущие данные
        self.students_data.clear()
        
        columns = ["Email", "Start Date", "End Date", "Progress (%)", "Expected result"]

        for table_div in tables:
            course_id = table_div.get("data-course-id")
            table = table_div.find("table", {"class": "lp-progress-table"})
            
            if not table:
                continue

            # Получаем индексы столбцов
            headers = table.find("tr").find_all("th")
            col_indices = {
                header.get_text(strip=True): idx 
                for idx, header in enumerate(headers)
                if header.get_text(strip=True) in columns
            }

            # Проверяем наличие всех нужных столбцов
            if not all(col in col_indices for col in columns):
                continue

            # Обрабатываем данные
            for row in table.find_all("tr")[1:]:
                cells = row.find_all("td")
                
                email = cells[col_indices["Email"]].get_text(strip=True)
                start_date = cells[col_indices["Start Date"]].get_text(strip=True)
                end_date = cells[col_indices["End Date"]].get_text(strip=True)
                progress = cells[col_indices["Progress (%)"]].get_text(strip=True)
                expected_result = cells[col_indices["Expected result"]].get_text(strip=True)

                # Пропускаем студентов по условиям
                if (start_date == "N/A" or 
                    end_date or 
                    (progress and float(progress.replace("%", "")) > 80)):
                    continue

                # Сохраняем данные студента
                self.students_data[email] = StudentProgress(
                    email=email,
                    start_date=start_date if start_date != "N/A" else None,
                    end_date=end_date if end_date != "N/A" else None,
                    progress=float(progress.replace("%", "")) if progress else 0,
                    expected_result=float(expected_result) if expected_result else 0,
                    course_id=course_id
                )

    def get_student_progress(self, email: str) -> Optional[StudentProgress]:
        """Получение прогресса студента по email"""
        return self.students_data.get(email.lower())