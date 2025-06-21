from flask import Blueprint

# Blueprint for image deduplication features
image_dedup_bp = Blueprint('image_dedup',
                           __name__,
                           template_folder='templates',
                           static_folder='static', # if you plan to have module-specific static files
                           url_prefix='/img_duplicate') # Matches original /img_duplicate prefix

from . import routes # Import routes
# from . import utils # If you create a utils.py for this module
# from . import models # If you have models specific to this module
