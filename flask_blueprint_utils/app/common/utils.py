import re
import os
from werkzeug.utils import secure_filename
from flask import current_app

# Allowed image extensions, can be made configurable
ALLOWED_EXTENSIONS_IMG = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

def allowed_file(filename, allowed_extensions=ALLOWED_EXTENSIONS_IMG):
    """Checks if the file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def natural_sort_key(s):
    """Sort strings containing numbers in natural order."""
    if not isinstance(s, str): # Handle cases where s might not be a string
        return [s]
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', s)]

def get_secure_filename(filename_str):
    """Generates a secure version of a filename."""
    return secure_filename(filename_str)

# Example of a utility that might need app context for config
def get_upload_folder_path(folder_key_in_config):
    """
    Gets the absolute path for a configured upload folder.
    Example: get_upload_folder_path('IMG_DUP_UPLOAD_FOLDER')
    """
    if current_app:
        path = current_app.config.get(folder_key_in_config)
        if path:
            # Ensure the path is absolute. If it's relative, it's often relative to app root or instance.
            # The Config class now makes them absolute from BASE_DIR.
            return path
    # Fallback or error if path not found or app not available
    # This depends on how critical the path is outside app context
    return None


# You can add other shared utility functions here, for example,
# functions related to file operations, string manipulation, etc.
# that are used across multiple blueprints.
# For instance, the `add_text_to_image` function could be here if used by multiple modules,
# or in a specific `image_utils.py` within `app.common` if it's part of a larger image utility set.
# For now, `add_text_to_image` seems more specific to image generation/merging features.

def create_directory_if_not_exists(dir_path):
    """Creates a directory if it doesn't already exist."""
    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path)
            if current_app:
                current_app.logger.info(f"Created directory: {dir_path}")
        except OSError as e:
            if current_app:
                current_app.logger.error(f"Error creating directory {dir_path}: {e}")
            else:
                print(f"Error creating directory {dir_path}: {e}") # Fallback for non-app context
            raise # Re-raise the exception if critical
    elif not os.path.isdir(dir_path):
        msg = f"Path {dir_path} exists but is not a directory."
        if current_app:
            current_app.logger.error(msg)
        else:
            print(msg)
        raise NotADirectoryError(msg)

# The ImageProcessor class and its dependencies (HashProcessor, HistProcessor, DeepProcessor)
# from the original `processors` and `utils` folders need a new home.
# A good place would be `app/common/image_processing.py` or a sub-package `app/common/image_processing/`.
# This is a significant piece of logic. For now, this file only contains general utilities.
# Step 10 of the plan is to handle shared utilities and models, which will include this.
# So, the `ImageProcessor` will be created/moved in that step.
