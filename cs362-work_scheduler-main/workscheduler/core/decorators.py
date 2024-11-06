from functools import wraps
from flask import session, redirect, url_for
from classes.user import User

# Decorator to protect routes that require login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Decorator to ensure the user is an admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = User.query.filter_by(username=session.get('username')).first()
        if not user or user.role != 'admin':
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function