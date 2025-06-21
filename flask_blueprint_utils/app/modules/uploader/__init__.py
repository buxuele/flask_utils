from flask import Blueprint

# Blueprint for the simple image uploader utility
uploader_bp = Blueprint('uploader',
                        __name__,
                        template_folder='templates',
                        url_prefix='/uploader') # URL prefix for this module

# Import routes after Blueprint creation
from . import routes # noqa: E402,F401
