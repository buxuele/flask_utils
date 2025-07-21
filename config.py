import os


class Config:
    MAX_CONTENT_LENGTH = 64 * 1024 * 1024  # 64MB
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev_key')
