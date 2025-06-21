from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy extension instance
# This object will be configured with the Flask app in the app factory (create_app)
db = SQLAlchemy()
