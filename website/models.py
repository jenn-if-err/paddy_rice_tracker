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
    password = db.Column(db.String(200), nullable=False)

    municipality_id = db.Column(db.Integer, db.ForeignKey('municipalities.id'), nullable=True)
    municipality = db.relationship('Municipality', backref=db.backref('users', lazy=True))

    barangay_id = db.Column(db.Integer, db.ForeignKey('barangays.id'), nullable=True)
    barangay = db.relationship('Barangay', backref=db.backref('users', lazy=True))

    records = db.relationship('DryingRecord', backref='author', lazy=True)

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
    password = db.Column(db.String(150), nullable=False)

    barangay_id = db.Column(db.Integer, db.ForeignKey('barangays.id'), nullable=False)
    barangay = db.relationship('Barangay', backref=db.backref('farmers', lazy=True))

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('farmers', lazy=True))

    records = db.relationship('DryingRecord', back_populates='farmer', lazy=True)

    def get_id(self):
        return f"farmer-{self.id}"

    @property
    def role(self):
        return 'farmer'

    @property
    def full_name(self):
        return f"{self.first_name} {self.middle_name + ' ' if self.middle_name else ''}{self.last_name}"

# ==========================
# Drying Records Table
# ==========================
class DryingRecord(db.Model):
    __tablename__ = 'drying_records'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime(timezone=True), default=func.now())
    batch_name = db.Column(db.String(150), nullable=False)
    farmer_name = db.Column(db.String(150), nullable=True)

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
    due_date = db.Column(db.Date)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    farmer_id = db.Column(db.Integer, db.ForeignKey('farmers.id'), nullable=True)
    barangay_id = db.Column(db.Integer, db.ForeignKey('barangays.id'), nullable=True)
    municipality_id = db.Column(db.Integer, db.ForeignKey('municipalities.id'), nullable=True)

    farmer = db.relationship('Farmer', back_populates='records')
    barangay = db.relationship('Barangay', backref=db.backref('drying_records', lazy=True))
    municipality = db.relationship('Municipality', backref=db.backref('drying_records', lazy=True))

# =====================
# Municipality Model
# =====================
class Municipality(db.Model):
    __tablename__ = 'municipalities'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, unique=True)
    barangays = db.relationship('Barangay', backref='municipality', lazy=True)

# =================
# Barangay Model
# =================
class Barangay(db.Model):
    __tablename__ = 'barangays'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    municipality_id = db.Column(db.Integer, db.ForeignKey('municipalities.id'), nullable=False)

    __table_args__ = (db.UniqueConstraint('name', 'municipality_id', name='uq_barangay_name_per_municipality'),)
