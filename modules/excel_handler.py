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
    name: str
    progress: float
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
        self.required_columns = ["1 поток", "1 модуль"]
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
            if "1 поток" not in df.columns:
                print("Error: Column '1 поток' not found in Excel file")
                return False
                
            df = df[self.required_columns].dropna().reset_index(drop=True)
            print("\nLoaded student data:")
            print(df)
            
            # Обновление словаря с данными студентов
            self.students_data.clear()
            for _, row in df.iterrows():
                student_name = str(row["1 поток"]).strip().lower()
                print(f"Processing student: {student_name}")
                self.students_data[student_name] = StudentData(
                    name=student_name,
                    progress=float(row["1 модуль"]) if pd.notnull(row["1 модуль"]) else 0.0
                )
            
            print("\nProcessed students in memory:")
            for name, data in self.students_data.items():
                print(f"- {name}: {data.progress}%")
            
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

    def get_student_progress(self, full_name: str) -> Optional[StudentData]:
        """
        Получение прогресса студента по имени
        Args:
            full_name: Полное имя студента
        Returns:
            Optional[StudentData]: Данные студента или None
        """
        search_name = full_name.strip().lower()
        print(f"\nSearching for student: {search_name}")
        print("Available students:", list(self.students_data.keys()))
        
        # Точное совпадение
        if search_name in self.students_data:
            print(f"Exact match found for: {search_name}")
            return self.students_data[search_name]
            
        # Поиск частичного совпадения
        for name in self.students_data:
            if search_name in name or name in search_name:
                print(f"Partial match found: {name}")
                return self.students_data[name]
        
        print(f"No match found for: {search_name}")
        return None


    def generate_progress_prompt(self, progress: float) -> str:
        """
        Генерация промпта для OpenAI в зависимости от прогресса
        Args:
            progress: Процент прогресса
        Returns:
            str: Промпт для OpenAI
        """
        if 0 <= progress <= 0.20:
            return (
                f"Студент имеет прогресс {progress * 100}%. Сгенерируй мотивирующее сообщение "
                "с легким подзатыльником, которое поможет ему начать активнее учиться. "
                "Важно быть настойчивым."
            )
        elif 0.20 < progress <= 0.5:
            return (
                f"Студент имеет прогресс {progress * 100}%. Сгенерируй мотивирующее сообщение, "
                "которое отметит его старания и подбодрит делать больше."
            )
        elif 0.5 < progress <= 0.8:
            return (
                f"Студент имеет прогресс {progress * 100}%. Сгенерируй ободряющее сообщение, "
                "подчеркивающее, что он молодец и уже близок к цели."
            )
        elif 0.8 < progress < 1:
            return (
                f"Студент имеет прогресс {progress * 100}%. Сгенерируй воодушевляющее сообщение, "
                "подчеркивающее, что осталось совсем немного до полного завершения."
            )
        else:  # 100%
            return (
                "Студент выполнил 100% модуля! Сгенерируй радостное поздравление "
                "с успешным завершением модуля."
            )

        
    