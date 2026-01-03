from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Vehicle(db.Model):
    """Vehicle model to store vehicle owner information"""
    __tablename__ = 'vehicles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    vehicle_number = db.Column(db.String(20), unique=True, nullable=False, index=True)  # License plate number
    telegram_chat_id = db.Column(db.String(50), nullable=True, index=True)  # Telegram chat ID for notifications
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """Convert vehicle to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'phone_number': self.phone_number,
            'vehicle_number': self.vehicle_number,
            'telegram_chat_id': self.telegram_chat_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Vehicle {self.vehicle_number} - {self.name}>'

