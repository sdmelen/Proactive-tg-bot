from sqlalchemy.orm import Session
from models.models import User, Message
from models.database import get_db

class DatabaseService:
    def __init__(self):
        self.db = next(get_db())

    def save_user(self, chat_id: int, email: str) -> User:
        """Сохранение или обновление пользователя"""
        user = self.db.query(User).filter(User.chat_id == chat_id).first()
        if not user:
            user = User(chat_id=chat_id, email=email, verified=True)
            self.db.add(user)
        else:
            user.email = email
            user.verified = True
        self.db.commit()
        return user

    def get_user_by_chat_id(self, chat_id: int) -> User:
        """Получение пользователя по chat_id"""
        return self.db.query(User).filter(User.chat_id == chat_id).first()

    def get_user_by_email(self, email: str) -> User:
        """Получение пользователя по email"""
        return self.db.query(User).filter(User.email == email).first()

    def save_message(self, chat_id: int, message_id: int, user_id: int, 
                    role: str, content: str) -> Message:
        """Сохранение сообщения"""
        message = Message(
            chat_id=chat_id,
            message_id=message_id,
            user_id=user_id,
            role=role,
            content=content
        )
        self.db.add(message)
        self.db.commit()
        return message

    def get_chat_history(self, chat_id: int, limit: int = 6) -> list:
        """Получение истории сообщений чата"""
        return self.db.query(Message)\
            .filter(Message.chat_id == chat_id)\
            .order_by(Message.created_at.desc())\
            .limit(limit)\
            .all()