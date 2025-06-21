import os
from app import create_app

# Load environment variables if you are using a .env file
# from dotenv import load_dotenv
# load_dotenv()

# Create an application instance
# The 'default' config name will look for Config in config.py,
# or you can specify another one e.g. 'development', 'production'
# if you have multiple config classes in config.py
app = create_app(os.getenv('FLASK_CONFIG') or 'default')

if __name__ == '__main__':
    # The host and port can also be moved to Config if preferred
    app.run(host='0.0.0.0', port=5080, debug=True)
    # The print statement from the original app.py is not needed here
    # as Flask's development server provides this information.
