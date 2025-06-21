from flask import Blueprint

# Create a Blueprint for the 'prompts' module
# The first argument is the Blueprint's name, which is used by Flask's routing internals.
# The second argument, __name__, helps locate the Blueprint's resources (like templates and static files).
# url_prefix will ensure all routes in this blueprint are prefixed with '/prompts'
prompts_bp = Blueprint('prompts', __name__, template_folder='templates', url_prefix='/prompts')

# Import routes after Blueprint creation to avoid circular imports
from . import routes # noqa: E402,F401
