from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# User model
class User(db.Model):
    __tablename__ = 'users'
    username = db.Column(db.String(80), primary_key=True)
    password_hash = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    sick_hours = db.Column(db.Float, default=0)
    pto_hours = db.Column(db.Float, default=0)
    hourly_rate = db.Column(db.Float)
    job_assignment = db.Column(db.String(80))
    hire_date = db.Column(db.String(20))
    role = db.Column(db.String(20), default='employee')
    schedules = db.relationship('Schedule', backref='user', lazy=True)

    # Password methods
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)