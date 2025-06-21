from flask import Blueprint

# Blueprint for file difference utility
file_diff_bp = Blueprint('file_diff',
                         __name__,
                         template_folder='templates',
                         url_prefix='/file-diff') # URL prefix for this module

# Import routes after Blueprint creation
from . import routes # noqa: E402,F401
