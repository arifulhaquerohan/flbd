from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user') # user, designer, admin
    flats = db.relationship('Flat', backref='owner', lazy=True)
    interior_listings = db.relationship('InteriorService', backref='provider', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

class Flat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    area_sqft = db.Column(db.Integer)
    bhk = db.Column(db.Integer)
    image_url = db.Column(db.String(500))
    status = db.Column(db.String(20), default='pending') # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class InteriorService(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    provider_name = db.Column(db.String(100), nullable=False)
    service_type = db.Column(db.String(100), nullable=False) # Full house, kitchen, etc
    description = db.Column(db.Text, nullable=False)
    starting_price = db.Column(db.Float)
    image_url = db.Column(db.String(500))
    portfolio_url = db.Column(db.String(500))
    status = db.Column(db.String(20), default='pending') # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(40))
    email = db.Column(db.String(120))
    interest = db.Column(db.String(40))
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='new') # new, contacted, closed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
