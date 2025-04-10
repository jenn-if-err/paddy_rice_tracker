from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy.sql import func
from .extensions import db

# ================================
# User (Barangay & Municipal Staff)
# ================================
class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'barangay' or 'municipal'
    barangay_name = db.Column(db.String(150), nullable=True)
    password = db.Column(db.String(200), nullable=False)  # Password for authentication

    # Relationship to DryingRecord
    records = db.relationship('DryingRecord', backref='author', lazy=True)

    # Override get_id to return a prefixed ID
    def get_id(self):
        return f"user-{self.id}"

# ========================
# Farmer Model
# ========================
class Farmer(db.Model, UserMixin):
    __tablename__ = 'farmers'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(150), nullable=False)
    middle_name = db.Column(db.String(150), nullable=True)
    last_name = db.Column(db.String(150), nullable=False)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)  # Store hashed password
    barangay_name = db.Column(db.String(150), nullable=False)  # Farmer must belong to a Barangay

    # Relationship to DryingRecord
    records = db.relationship('DryingRecord', back_populates='farmer', lazy=True)

    # Foreign Key: A Farmer is linked to a Barangay (via User)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('farmers', lazy=True))

    # Override get_id to return a prefixed ID
    def get_id(self):
        return f"farmer-{self.id}"

    # Add role attribute for consistency in templates
    @property
    def role(self):
        return 'farmer'
        
    # Add full_name property for consistency (optional but helpful)
    @property
    def full_name(self):
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        else:
            return f"{self.first_name} {self.last_name}"

# ==========================
# Drying Records Table
# ==========================
class DryingRecord(db.Model):
    __tablename__ = 'drying_records'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime(timezone=True), default=func.now())
    batch_name = db.Column(db.String(150), nullable=False)
    farmer_name = db.Column(db.String(150), nullable=True)

    # Drying sensor values
    initial_weight = db.Column(db.Float, nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    humidity = db.Column(db.Float, nullable=False)
    sensor_value = db.Column(db.Float, nullable=False)
    initial_moisture = db.Column(db.Float, nullable=False)
    final_moisture = db.Column(db.Float, nullable=False)
    drying_time = db.Column(db.String(50), nullable=False)
    final_weight = db.Column(db.Float, nullable=False)
    shelf_life = db.Column(db.String(50), nullable=True)

    date_dried = db.Column(db.Date)
    date_planted = db.Column(db.Date)
    date_harvested = db.Column(db.Date)

    barangay_name = db.Column(db.String(150), nullable=True)

    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    farmer_id = db.Column(db.Integer, db.ForeignKey('farmers.id'), nullable=True)

    # Optional: Adding relationship with Farmer to avoid the naming conflict
    farmer = db.relationship('Farmer', back_populates='records', foreign_keys=[farmer_id])

    due_date = db.Column(db.Date)
