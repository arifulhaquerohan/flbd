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
    __table_args__ = (
        db.Index('idx_flat_status_created', 'status', 'created_at'),
    )
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False, index=True)
    location = db.Column(db.String(100), nullable=False, index=True)
    area_sqft = db.Column(db.Integer)
    bhk = db.Column(db.Integer, index=True)
    image_url = db.Column(db.String(500))
    video_url = db.Column(db.String(500))
    status = db.Column(db.String(20), default='pending', index=True) # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)

class InteriorService(db.Model):
    __table_args__ = (
        db.Index('idx_interior_status_created', 'status', 'created_at'),
    )
    id = db.Column(db.Integer, primary_key=True)
    provider_name = db.Column(db.String(100), nullable=False)
    service_type = db.Column(db.String(100), nullable=False, index=True) # Full house, kitchen, etc
    description = db.Column(db.Text, nullable=False)
    starting_price = db.Column(db.Float, index=True)
    image_url = db.Column(db.String(500))
    portfolio_url = db.Column(db.String(500))
    status = db.Column(db.String(20), default='pending', index=True) # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)

class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(40))
    email = db.Column(db.String(120))
    interest = db.Column(db.String(40))
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='new', index=True) # new, contacted, closed
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
