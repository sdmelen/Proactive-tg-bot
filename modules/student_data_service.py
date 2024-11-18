import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict
import requests
from bs4 import BeautifulSoup
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
        """Инициализация сервиса с данными для авторизации"""
        self.login_url = "https://aumit.us/wp-login.php?itsec-hb-token=amazing-aumit"
        self.data_url = "https://aumit.us/studresult/"
        self.username = os.getenv('AUMIT_USERNAME')
        self.password = os.getenv('AUMIT_PASSWORD')
        self.students_data: Dict[str, StudentProgress] = {}
        self.session = requests.Session()

    def update_data(self) -> bool:
        """Обновление данных студентов"""
        try:
            # Подготовка данных для авторизации
            login_payload = {
                "log": self.username,
                "pwd": self.password,
                "wp-submit": "Log In",
                "testcookie": "1"
            }

            # Авторизация
            login_response = self.session.post(self.login_url, data=login_payload)
            if not login_response.ok or "incorrect" in login_response.text:
                print("Authentication failed")
                return False

            # Получение данных
            page_response = self.session.get(self.data_url)
            if page_response.status_code != 200:
                print(f"Failed to get data page. Status: {page_response.status_code}")
                return False

            # Парсинг данных
            self._parse_data(page_response.content)
            return True

        except Exception as e:
            print(f"Error updating student data: {str(e)}")
            return False

    def _parse_data(self, content: bytes) -> None:
        """Парсинг HTML и обновление данных студентов"""
        soup = BeautifulSoup(content, 'html.parser')
        tables = soup.find_all("div", {"class": "lp-student-progress-table"})
        
        # Очищаем текущие данные
        self.students_data.clear()
        
        columns = ["Email", "Start Date", "End Date", "Progress (%)", "Expected result"]

        for table_div in tables:
            course_id = table_div.get("data-course-id", "Unknown")
            table = table_div.find("table", {"class": "lp-progress-table"})
            
            if not table:
                continue

            # Получаем индексы столбцов
            header_cells = table.find("tr").find_all("th")
            col_indices = {
                header.get_text(strip=True): idx 
                for idx, header in enumerate(header_cells)
                if header.get_text(strip=True) in columns
            }

            # Проверяем наличие всех нужных столбцов
            if not all(col in col_indices for col in columns):
                continue

            # Обрабатываем данные
            for row in table.find_all("tr")[1:]:
                cells = row.find_all("td")
                if len(cells) < len(col_indices):
                    continue

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
                try:
                    progress_value = float(progress.replace("%", "")) if progress else 0
                    expected_value = float(expected_result) if expected_result else 0
                    
                    self.students_data[email.lower()] = StudentProgress(
                        email=email,
                        start_date=start_date if start_date != "N/A" else None,
                        end_date=end_date if end_date != "N/A" else None,
                        progress=progress_value,
                        expected_result=expected_value,
                        course_id=course_id
                    )
                except (ValueError, TypeError) as e:
                    print(f"Error processing student data for {email}: {str(e)}")

    def get_student_progress(self, email: str) -> Optional[StudentProgress]:
        """Получение прогресса студента по email"""
        return self.students_data.get(email.lower())