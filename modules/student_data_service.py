import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict
import requests
from dotenv import load_dotenv
from .logger import BotLogger

load_dotenv()

@dataclass
class StudentProgress:
    email: str
    name: str
    course_id: str
    status: str
    expected_result: int
    created_at: datetime = datetime.now()

class StudentDataService:
    def __init__(self, logger: BotLogger):
        """Инициализация сервиса с данными для API"""
        self.api_url = "https://aumit.us/wp-json/student-progress/v1/course-data/"
        self.api_key = os.getenv('BOT_TOKEN')
        self.students_data: Dict[str, StudentProgress] = {}
        self.logger = logger

    def update_data(self) -> bool:
        """Обновление данных студентов через API"""
        try:
            headers = {
                'x-api-key': self.api_key
            }
            
            response = requests.get(self.api_url, headers=headers)
            
            if response.status_code != 200:
                self.logger.log_api_request(
                    endpoint=self.api_url,
                    status_code=response.status_code,
                    error=response.text
                )
                return False

            # Обновляем данные
            data = response.json()
            
            import json
            print("\nСырые данные от API:")
            print(json.dumps(data, indent=2))   
            
            self.students_data.clear()
            
            for record in data:
                email = record.get("user_email", "").lower()
                if not email:  # Пропускаем только записи без email
                    continue
                    
                student = StudentProgress(
                    email=email,
                    name=record.get("user_name", ""),
                    course_id=record.get("course_id", ""),
                    status=record.get("status", ""),
                    expected_result=int(record.get("expected_progress_difference", 0))
                )
                
                self.students_data[email] = student
                self.logger.log_student_update(email, student.expected_result)
                
                self.logger.logger.info(f"Updated data for {len(self.students_data)} students")
            
            # # Отладочный вывод
            # print(f"\nОбновлены данные для {len(self.students_data)} студентов:")
            # for student in self.students_data.values():
            #     print(f"""
            #     Имя: {student.name}
            #     Email: {student.email}
            #     Курс: {student.course_id}
            #     Статус: {student.status}
            #     Result: {student.expected_result}
            #     ------------------------""")
            
            return True

        except Exception as e:
            self.logger.logger.error(f"Error updating student data: {str(e)}", exc_info=True)
            return False

    def get_student_progress(self, email: str) -> Optional[StudentProgress]:
        try:
            student = self.students_data.get(email.lower())
            if student:
                self.logger.logger.info(f"Retrieved progress for student: {email}")
            else:
                self.logger.logger.warning(f"Student not found: {email}")
            return student
        except Exception as e:
            self.logger.logger.error(f"Error retrieving student progress: {str(e)}", exc_info=True)
            return None