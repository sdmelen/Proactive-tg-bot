from models.database import init_db

if __name__ == "__main__":
    print("Creating database tables...")
    init_db()
    print("Tables created successfully!")