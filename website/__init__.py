from flask import Flask, jsonify, request, redirect, url_for
import os
from dotenv import load_dotenv, find_dotenv
from .extensions import db, login_manager, migrate
from .api import api as api_blueprint
from .auth import auth, google_bp
from .views import views

def create_app():
    load_dotenv(find_dotenv()) 
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "dev-secret")
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "postgresql://paddy_rice_tracker_db_user:2RX9usq562ns4fB04L8Y2tsJAVD1YTaV@dpg-cvrqgq6r433s73b1sbng-a/paddy_rice_tracker_db")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    print(" Loaded DB URI:", app.config['SQLALCHEMY_DATABASE_URI'])

    # Extensions
    db.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = ''
    login_manager.init_app(app)

    # unauthorized handler override to allow public API access
    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith("/api"):
            return jsonify({"error": "Unauthorized"}), 401
        return redirect(url_for(login_manager.login_view))

    # Blueprints
    app.register_blueprint(auth, url_prefix="/")
    app.register_blueprint(api_blueprint, url_prefix='/api')
    app.register_blueprint(google_bp, url_prefix="/login")
    app.register_blueprint(views, url_prefix="/")

    # Models (import within context)
    with app.app_context():
        from .models import User, Farmer, DryingRecord, Municipality, Barangay
        #db.create_all()  # enable during first-time setup

    # Load user for Flask-Login
    @login_manager.user_loader
    def load_user(user_id_str):
        from .models import User, Farmer

        try:
            prefix, user_id = user_id_str.split('-', 1)
            user_id = int(user_id)
        except (ValueError, AttributeError):
            return None

        if prefix == 'user':
            return User.query.get(user_id)
        elif prefix == 'farmer':
            return Farmer.query.get(user_id)
        return None

    return app
