import os


class Config:

    USER_UPLOAD_FOLDER = 'static/user_uploads'
    IMG_DUP_UPLOAD_FOLDER = 'static/img_dup_uploads'
    THUMBNAIL_FOLDER = 'static/thumbnails'
    DUPLICATES_FOLDER = 'static/duplicates'
    REMOVE_DUP_FOLDER = 'static/remove_dup'
    
    MAX_CONTENT_LENGTH = 64 * 1024 * 1024  # 64MB
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev_key')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///prompts.db' 

    def __init__(self):
        os.makedirs(self.USER_UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(self.IMG_DUP_UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(self.THUMBNAIL_FOLDER, exist_ok=True)
        os.makedirs(self.DUPLICATES_FOLDER, exist_ok=True)
        os.makedirs(self.REMOVE_DUP_FOLDER, exist_ok=True)
