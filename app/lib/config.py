# app/lib/config.py

import os
from dotenv import load_dotenv

load_dotenv()


class PineconeConfig:
    def __init__(self):
        self.api_key: str = os.getenv("PINECONE_API_KEY", "xxx-xxx")
        self.profile_index: str = os.getenv("PINECONE_PROFILE_INDEX", "dev-profile-memory")


class DatabaseConfig:
    def __init__(self):
        self.url: str = os.environ["DATABASE_URL"]


class Config:
    def __init__(self):
        self.pinecone = PineconeConfig()
        self.database = DatabaseConfig()


config = Config()