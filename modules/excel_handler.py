from typing import Optional, Dict
import pandas as pd
import asyncio
import datetime
import sys
import os
from dataclasses import dataclass, field
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import BotConfig

@dataclass
class StudentData:
    email: str
    delta_progress: float
    last_update: datetime.datetime = field(default_factory=datetime.datetime.now)

class ExcelHandler:
    def __init__(self, config: BotConfig):
        """
        Инициализация обработчика Excel
        Args:
            config: конфигурация бота
        """
        self.file_path = config.excel_file_path
        self.update_interval = config.update_interval
        self.required_columns = ["email", "Delta Progress"]
        self.students_data: Dict[str, StudentData] = {}
        self.last_update: Optional[datetime.datetime] = None
        # Сразу загружаем данные при инициализации
        self.update_data_sync()

    def update_data_sync(self) -> bool:
        """
        Синхронное обновление данных из Excel файла при инициализации
        """
        try:
            print(f"Reading Excel file from: {self.file_path}")
            df = pd.read_excel(self.file_path)
            print("Excel columns found:", df.columns.tolist())
            
            # Проверяем наличие требуемых столбцов
            if not all(col in df.columns for col in self.required_columns):
                missing = [col for col in self.required_columns if col not in df.columns]
                print(f"Error: Columns {missing} not found in Excel file")
                return False
                
            df = df[self.required_columns].dropna().reset_index(drop=True)
            print("\nLoaded student data:")
            print(df)
            
            # Обновление словаря с данными студентов
            self.students_data.clear()
            for _, row in df.iterrows():
                email = str(row["email"]).strip().lower()
                print(f"Processing student: {email}")
                self.students_data[email] = StudentData(
                    email=email,
                    delta_progress=float(row["Delta Progress"]) if pd.notnull(row["Delta Progress"]) else 0.0
                )
            
            print("\nProcessed students in memory:")
            for email, data in self.students_data.items():
                print(f"- {email}: DP={data.delta_progress}")
            
            self.last_update = datetime.datetime.now()
            return True
            
        except Exception as e:
            print(f"Error updating Excel data: {str(e)}")
            return False

    async def update_data(self) -> bool:
        """
        Асинхронное обновление данных из Excel файла
        """
        return self.update_data_sync()

    def get_student_progress(self, email: str) -> Optional[StudentData]:
        """
        Получение прогресса студента по email
        Args:
            email: Email студента
        Returns:
            Optional[StudentData]: Данные студента или None
        """
        search_email = email.strip().lower()
        print(f"\nSearching for student: {search_email}")
        print("Available emails:", list(self.students_data.keys()))
        
        # Точное совпадение
        if search_email in self.students_data:
            print(f"Exact match found for: {search_email}")
            return self.students_data[search_email]
        
        print(f"No match found for: {search_email}")
        return None

    def generate_progress_prompt(self, delta_progress: float) -> str:
        """
        Генерация промпта для OpenAI в зависимости от значения Delta Progress
        Args:
            delta_progress: Значение Delta Progress
        Returns:
            str: Промпт для OpenAI
        """
        print(f"Generating prompt for Delta Progress: {delta_progress}")
        
        if delta_progress > 3:
            print("Case: High achiever")
            return (
                f"Student has Delta Progress = {delta_progress}. This means that he "
                "is significantly ahead of the pace of the course. Generate an encouraging message, "
                "which praises him for his excellent results and motivation to learn."
            )
        elif 0 <= delta_progress <= 3:
            print("Case: On track")
            return (
                f"Student has Delta Progress = {delta_progress}. This means that he "
                "is going exactly at the pace of the course. Generate a positive message, "
                "which confirms that he is doing everything right and supports him."
            )
        elif -4 <= delta_progress < 0:
            print("Case: Slight underperformer")
            return (
                f"Student has Delta Progress = {delta_progress}. This means that he "
                "slightly behind the pace of the course. Generate a soft motivating message "
                "with a light humorous rebuke that will encourage him to catch up."
            )
        elif -10 <= delta_progress < -4:
            print("Case: Basic underperformer")
            return (
                f"Student has Delta Progress = {delta_progress}. This means that he "
                "is lagging behind the pace of the course. Generate a half-joking message, "
                "which will indicate the problem of lagging and the importance of solving it, "
                "but at the same time support the student and say that it's okay and it could have been worse"
            )
        else:  # delta_progress < -10
            return (
                f"Student has Delta Progress = {delta_progress}. This means a critical "
                "ag behind the pace of the course. Generate a strict but constructive message, "
                "which will seriously indicate the catastrophism of the situation and the need for urgent "
                "actions to remedy the situation. Add specific tips for organizing training."
            )
