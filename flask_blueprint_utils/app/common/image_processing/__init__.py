# This file makes 'image_processing' a Python package.

# We can expose the main ImageProcessor class and its components here for easier import.
# For example, if HashProcessor is in hash_helper.py:
from .hash_helper import HashProcessor
from .hist_helper import HistProcessor
from .deep_helper import DeepProcessor
from .base_processor import ImageProcessor

# This makes these classes available when importing from app.common.image_processing
# e.g., from app.common.image_processing import ImageProcessor
