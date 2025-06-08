import os
from dotenv import load_dotenv

load_dotenv()  # Load from .env

class Settings:
    # API Keys
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # Database settings
    CHROMA_DB_PATH = "./data/chroma_db"
    UPLOAD_DIR = "./data/uploads"
    
    # Model settings
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    GEMINI_MODEL = "models/gemini-1.5-flash"
    
    # Processing settings
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    
    # OCR settings
    TESSERACT_CMD = os.getenv("TESSERACT_CMD")

    def __init__(self):
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        os.makedirs(os.path.dirname(self.CHROMA_DB_PATH), exist_ok=True)

settings = Settings()
