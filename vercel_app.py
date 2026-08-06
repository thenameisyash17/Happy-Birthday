# ============================================================
# VERCEL COMPATIBLE ENTRY POINT
# This file is specifically for Vercel deployment
# ============================================================

import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime

# ============================================================
# APP CREATION
# ============================================================
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'yash-world-secret-key-2024')

# ============================================================
# DATABASE CONFIGURATION - MOCK FOR VERCEL
# ============================================================
# On Vercel, we use a simple in-memory dict instead of SQLAlchemy
# This allows the app to run without a database connection

class MockDB:
    """Mock database for Vercel deployment"""
    def __init__(self):
        self.users = {
            'yash': {'password': 'admin123', 'is_admin': True, 'is_friend': True},
            'Glory': {'password': 'lory', 'is_admin': False, 'is_friend': True}
        }
    
    def get_user(self, username):
        return self.users.get(username)
    
    def save_user(self, username, password, is_admin=False, is_friend=False):
        self.users[username] = {'password': password, 'is_admin': is_admin, 'is_friend': is_friend}

# Use mock database on Vercel
db = MockDB()
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class MockUser:
    def __init__(self, username, is_admin=False, is_friend=False):
        self.id = username
        self.username = username
        self.is_admin = is_admin
        self.is_friend = is_friend
        self.questions = []
        self.replies = []
    
    def set_password(self, password):
        self.password = password
    
    def check_password(self, password):
        return self.password == password
    
    def get_id(self):
        return self.username

@login_manager.user_loader
def load_user(user_id):
    user_data = db.get_user(user_id)
    if user_data:
        user = MockUser(user_id, user_data.get('is_admin', False), user_data.get('is_friend', False))
        user.password = user_data.get('password')
        return user
    return None

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You need admin access for this page.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# ============================================================
# ROUTES - AUTHENTICATION
# ============================================================

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        user_data = db.get_user(username)
        if user_data and user_data.get('password') == password:
            user = MockUser(username, user_data.get('is_admin', False), user_data.get('is_friend', False))
            login_user(user, remember=remember)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ============================================================
# ROUTES - DASHBOARD (Simplified for Vercel)
# ============================================================

@app.route('/dashboard')
@login_required
def dashboard():
    is_admin = current_user.is_admin
    is_friend = current_user.is_friend
    
    return render_template('dashboard.html', 
        questions=[],
        current_question=None,
        current_index=0,
        total_questions=0,
        is_admin=is_admin,
        is_friend=is_friend,
        current_user=current_user,
        feedback_questions=[],
        typing_text=None,
        show_typing=False
    )

# ============================================================
# ROUTES - ADMIN
# ============================================================

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = [{'username': 'yash', 'is_admin': True, 'is_friend': True, 'created_at': datetime.now()}]
    return render_template('admin_users.html', users=users)

# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error_code=404, message='Page not found'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('error.html', error_code=500, message='Internal server error'), 500

# ============================================================
# VERCEL ENTRY POINT
# ============================================================

# The 'app' object is what Vercel imports
# This is the handler for Vercel serverless functions

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
