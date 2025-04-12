from flask import Flask
import os
from dotenv import load_dotenv
from .extensions import db, login_manager, migrate
from .api import api
from .auth import auth, google_bp
from .views import views
from dotenv import load_dotenv, find_dotenv


def create_app():
    load_dotenv(find_dotenv()) 
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "dev-secret")
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "postgresql://paddy_rice_tracker_db_user:2RX9usq562ns4fB04L8Y2tsJAVD1YTaV@dpg-cvrqgq6r433s73b1sbng-a/paddy_rice_tracker_db")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    print(" Loaded DB URI:", app.config['SQLALCHEMY_DATABASE_URI'])
    # Initialize Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = ''
    login_manager.init_app(app)

    # Register Blueprints
    app.register_blueprint(auth, url_prefix="/")
    app.register_blueprint(api, url_prefix="/api")
    app.register_blueprint(google_bp, url_prefix="/login")
    app.register_blueprint(views, url_prefix="/")

    #Import models after db is initialized!
    with app.app_context():
        from .models import User, Farmer, DryingRecord, Municipality, Barangay
        
        # Create all tables
        #db.create_all()

    # Login user loader
    @login_manager.user_loader
    def load_user(user_id_str):
        from .models import User, Farmer # Import both models
        
        # User ID string is now prefixed, e.g., "user-1" or "farmer-5"
        try:
            prefix, user_id = user_id_str.split('-', 1)
            user_id = int(user_id)
        except (ValueError, AttributeError):
            # Invalid ID format in session
            return None

        if prefix == 'user':
            return User.query.get(user_id)
        elif prefix == 'farmer':
            return Farmer.query.get(user_id)
        else:
            # Unknown prefix
            return None

    return app
