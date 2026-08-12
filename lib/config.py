import os
from dotenv import load_dotenv
from typing import TypedDict
load_dotenv()

class PineconeConfig:
    def __init__(
        self,
        api_key: str,
        profile_index: str,
    ):
        self.api_key = api_key
        self.profile_index = profile_index


class DatabaseConfig:
    def __init__(self, url: str):
        self.url = url


class Config:
    def __init__(
        self,
        pinecone: PineconeConfig,
        database: DatabaseConfig,
    ):
        self.pinecone = pinecone
        self.database = database


config = Config()