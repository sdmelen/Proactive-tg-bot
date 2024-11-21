import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict
import requests
from dotenv import load_dotenv

load_dotenv()

@dataclass
class StudentProgress:
    email: str
    name: str
    course_id: str
    status: str
    progress: float
    expected_result: int
    created_at: datetime = datetime.now()

class StudentDataService:
    def __init__(self):
        """Инициализация сервиса с данными для API"""
        self.api_url = "https://aumit.us/wp-json/student-progress/v1/course-data/"
        self.api_key = os.getenv('BOT_TOKEN')
        self.students_data: Dict[str, StudentProgress] = {}

    def update_data(self) -> bool:
        """Обновление данных студентов через API"""
        try:
            headers = {
                'x-api-key': self.api_key
            }
            
            response = requests.get(self.api_url, headers=headers)
            
            if response.status_code != 200:
                print(f"API request failed with status code: {response.status_code}")
                return False

            # Обновляем данные
            self.students_data.clear()
            data = response.json()
            
            for record in data:
                email = record.get("user_email", "").lower()
                if not email:  # Пропускаем только записи без email
                    continue
                    
                self.students_data[email] = StudentProgress(
                    email=email,
                    name=record.get("user_name", ""),
                    course_id=record.get("course_id", ""),
                    status=record.get("status", ""),
                    progress=float(record.get("progress", 0)),
                    expected_result=int(record.get("expected_progress_difference", 0))
                )
            
            # Отладочный вывод
            print(f"\nОбновлены данные для {len(self.students_data)} студентов:")
            for student in self.students_data.values():
                print(f"""
                Имя: {student.name}
                Email: {student.email}
                Курс: {student.course_id}
                Статус: {student.status}
                Прогресс: {student.progress}%
                Expected Result: {student.expected_result}
                ------------------------""")
            
            return True

        except Exception as e:
            print(f"Error updating student data: {str(e)}")
            return False

    def get_student_progress(self, email: str) -> Optional[StudentProgress]:
        """Получение прогресса студента по email"""
        return self.students_data.get(email.lower())