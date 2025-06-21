from flask import Blueprint

# Blueprint for image tools like merging, cleaning, etc.
image_tools_bp = Blueprint('image_tools',
                           __name__,
                           template_folder='templates',
                           url_prefix='/image-tools') # Define a URL prefix for all routes in this blueprint

# Import routes after Blueprint creation to avoid circular imports
from . import routes # noqa: E402,F401
# from . import utils # noqa: E402,F401, if you create a utils.py for this module
