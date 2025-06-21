import os

class Config:
    # Base directory of the application (flask_blueprint_utils/)
    BASE_DIR = os.path.abspath(os.path.dirname(__file__)) # Corrected: config.py is inside flask_blueprint_utils

    # Instance folder path, relative to BASE_DIR
    INSTANCE_FOLDER_PATH = os.path.join(BASE_DIR, 'instance')

    # --- Upload and Storage Directories ---
    # These are defined relative to BASE_DIR for clarity and ease of management.
    # All paths should be absolute for the application to use them reliably.

    # For 'uploader' module
    UPLOADER_STORAGE_DIR = os.path.join(BASE_DIR, 'uploads', 'general_uploads')

    # For 'image_dedup' (new deduplication tool) module
    IMG_DUP_UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads', 'image_dedup', 'uploads')
    IMG_DUP_THUMBNAIL_FOLDER = os.path.join(BASE_DIR, 'uploads', 'image_dedup', 'thumbnails')
    IMG_DUP_DUPLICATES_FOLDER = os.path.join(BASE_DIR, 'uploads', 'image_dedup', 'duplicates')

    # For 'legacy_image_diff' module
    LEGACY_IMAGE_DIFF_UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads', 'legacy_image_diff', 'uploads')
    LEGACY_IMAGE_DIFF_THUMBNAIL_DIR = os.path.join(BASE_DIR, 'uploads', 'legacy_image_diff', 'thumbnails')
    LEGACY_IMAGE_DIFF_DUPLICATES_DIR = os.path.join(BASE_DIR, 'uploads', 'legacy_image_diff', 'duplicates') # Replaces REMOVE_DUP_FOLDER

    # For 'image_tools' (specifically clean_images output)
    CLEANED_IMAGES_OUTPUT_DIR = os.path.join(BASE_DIR, 'outputs', 'cleaned_images')

    # Original USER_UPLOAD_FOLDER - can be deprecated if UPLOADER_STORAGE_DIR replaces its use.
    # For now, keeping it if any old logic might still reference it, but ideally phase out.
    # If UPLOADER_STORAGE_DIR is its replacement, this line can be removed.
    # USER_UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads', 'user_uploads_deprecated')


    # --- Application Settings ---
    MAX_CONTENT_LENGTH = 64 * 1024 * 1024  # 64MB
    SECRET_KEY = os.getenv('SECRET_KEY', 'a_very_secret_dev_key_please_change_me_in_production')

    # --- Database Settings ---
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(INSTANCE_FOLDER_PATH, 'prompts.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Allowed extensions for general image uploads (can be overridden by specific modules)
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'svg', 'ico', 'tif', 'tiff', 'avif'}


    @staticmethod
    def init_app(app):
        """Initializes application-specific configurations and creates necessary directories."""
        app.instance_path = Config.INSTANCE_FOLDER_PATH
        os.makedirs(app.instance_path, exist_ok=True)

        # List of all directories that need to be created
        # This ensures all modules have their storage locations ready.
        dirs_to_create = [
            Config.UPLOADER_STORAGE_DIR,
            Config.IMG_DUP_UPLOAD_FOLDER,
            Config.IMG_DUP_THUMBNAIL_FOLDER,
            Config.IMG_DUP_DUPLICATES_FOLDER,
            Config.LEGACY_IMAGE_DIFF_UPLOAD_DIR,
            Config.LEGACY_IMAGE_DIFF_THUMBNAIL_DIR,
            Config.LEGACY_IMAGE_DIFF_DUPLICATES_DIR,
            Config.CLEANED_IMAGES_OUTPUT_DIR,
            # Config.USER_UPLOAD_FOLDER, # If still used
        ]

        for dir_path in dirs_to_create:
            if dir_path: # Ensure path is not None
                os.makedirs(dir_path, exist_ok=True)
            else:
                if app and app.logger:
                    app.logger.warning(f"A configured directory path is None or empty and was not created.")

        if app and app.logger:
            app.logger.info("Initialized instance path and created necessary application directories.")

# Example of how to define different configurations for different environments:
# class DevelopmentConfig(Config):
#     DEBUG = True
#     SQLALCHEMY_ECHO = True # Log SQL queries

# class ProductionConfig(Config):
#     DEBUG = False
#     # Add other production-specific settings, e.g., from environment variables
#     # SECRET_KEY = os.environ.get('PROD_SECRET_KEY') # Ensure this is set in prod

# config_by_name = dict(
#     development=DevelopmentConfig,
#     production=ProductionConfig,
#     default=DevelopmentConfig # Default if FLASK_CONFIG not set
# )
