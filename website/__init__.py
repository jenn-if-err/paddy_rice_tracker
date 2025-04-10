from flask import Flask
import os
from dotenv import load_dotenv
from .extensions import db, login_manager, migrate
from .api import api
from .auth import auth, google_bp
from .views import views

def create_app():
    load_dotenv()
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "dev-secret")
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///local.db")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # ✅ Initialize Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    # ✅ Register Blueprints
    app.register_blueprint(auth, url_prefix="/")
    app.register_blueprint(api, url_prefix="/api")
    app.register_blueprint(google_bp, url_prefix="/login")
    app.register_blueprint(views, url_prefix="/")

    # ✅ Import models after db is initialized!
    with app.app_context():
        from .models import User, Farmer, DryingRecord
        db.create_all()

    # ✅ Login user loader
    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return User.query.get(int(user_id))

    return app
