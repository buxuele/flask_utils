import os
from flask import Flask, render_template, url_for, redirect # render_template for custom error pages & index, url_for/redirect for root
from config import Config # Import the base Config class

# Import extensions
from .extensions import db # Assuming db = SQLAlchemy() is in extensions.py

def create_app(config_name=None): # config_name can be 'development', 'production', etc. or None for default
    """
    Application factory function.
    Args:
        config_name: The environment to load config for (e.g., 'development', 'testing', 'production').
                     If None, uses the default Config.
    """
    app = Flask(__name__, instance_relative_config=True) # instance_relative_config=True allows instance folder config

    # Load configuration
    # This part needs to be more flexible if you have multiple config classes (e.g., DevConfig, ProdConfig)
    # For now, using the single Config class from config.py
    # You might have a dictionary like `config_by_name = dict(development=DevConfig, production=ProdConfig)`
    # and then `app.config.from_object(config_by_name.get(config_name, Config))`
    app.config.from_object(Config) # Directly load from the Config class

    # Ensure instance folder exists and initialize folders specified in Config
    # The Config.init_app method in the refactored config.py handles this.
    if hasattr(Config, 'init_app'):
        Config.init_app(app) # This creates upload folders and instance path
    else:
        # Fallback if Config class doesn't have init_app (it should)
        try:
            os.makedirs(app.instance_path, exist_ok=True)
            # Manually create other dirs if not handled by Config.init_app
            # This part should ideally be centralized in Config.init_app
            os.makedirs(app.config.get('USER_UPLOAD_FOLDER'), exist_ok=True)
            os.makedirs(app.config.get('IMG_DUP_UPLOAD_FOLDER'), exist_ok=True)
            # ... and so on for all configured directories
        except OSError as e:
            app.logger.error(f"Could not create instance/upload paths: {e}")
            pass
        except TypeError as e: # If a config path is None
             app.logger.error(f"A configured path is None, cannot create directory: {e}")


    # Initialize Flask extensions
    db.init_app(app)
    # Other extensions like Migrate, LoginManager, etc., would be initialized here:
    # from .extensions import migrate # Example
    # migrate.init_app(app, db)
    # login_manager.init_app(app)

    # Register Blueprints
    # Import blueprint objects here to avoid circular dependencies
    from .modules.prompts import prompts_bp
    from .modules.image_dedup import image_dedup_bp
    from .modules.image_tools import image_tools_bp
    from .modules.file_diff import file_diff_bp
    from .modules.legacy_image_diff import legacy_image_diff_bp
    from .modules.uploader import uploader_bp

    app.register_blueprint(prompts_bp)
    app.register_blueprint(image_dedup_bp)
    app.register_blueprint(image_tools_bp)
    app.register_blueprint(file_diff_bp)
    app.register_blueprint(legacy_image_diff_bp)
    app.register_blueprint(uploader_bp)

    # Create database tables if they don't exist (within app context)
    # This is suitable for development. For production, migrations (Flask-Migrate) are better.
    # Important: Ensure all models are imported (usually via blueprint imports) before calling create_all().
    with app.app_context():
        db.create_all()

    # Optional: Register a simple root route for the application.
    @app.route('/')
    def app_root():
        # Redirect to a default page, e.g., the image_tools merge page or a new index.
        # Example: return redirect(url_for('image_tools.merge_two_images_get'))
        # For now, let's render a simple global index page.
        # This requires flask_blueprint_utils/app/templates/index.html to be created.
        return render_template('index.html')

    # Optional: Register custom error handlers
    # @app.errorhandler(404)
    # def page_not_found(e):
    #     return render_template('errors/404.html'), 404 # Requires app/templates/errors/404.html

    # @app.errorhandler(500)
    # def internal_server_error(e):
    #     # db.session.rollback() # Optional: rollback session on error
    #     return render_template('errors/500.html'), 500 # Requires app/templates/errors/500.html

    app.logger.info(f"Flask application '{app.name}' created successfully using {Config.__name__}.")
    return app
