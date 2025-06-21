from flask import Blueprint

# Blueprint for the legacy image difference/deduplication tool
legacy_image_diff_bp = Blueprint('legacy_image_diff',
                                 __name__,
                                 template_folder='templates',
                                 # Static folder for this blueprint if it has specific static assets
                                 # static_folder='static',
                                 url_prefix='/legacy-image-diff') # New prefix to avoid conflict

# Import routes after Blueprint creation
from . import routes # noqa: E402,F401
