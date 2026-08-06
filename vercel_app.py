# ============================================================
# YASH WORLD - VERCEL COMPATIBLE VERSION
# Minimal working version with NO database dependencies
# ============================================================

import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from functools import wraps
from datetime import datetime

# ============================================================
# APP CREATION
# ============================================================
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'yash-world-secret-key-2024')
app.secret_key = app.config['SECRET_KEY']

# ============================================================
# LOGIN MANAGER
# ============================================================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ============================================================
# USER CLASS
# ============================================================
class User(UserMixin):
    def __init__(self, username, password, is_admin=False, is_friend=False):
        self.id = username
        self.username = username
        self.password = password
        self.is_admin = is_admin
        self.is_friend = is_friend
    
    def check_password(self, password):
        return self.password == password

# ============================================================
# USER STORE
# ============================================================
USERS = {
    'yash': User('yash', 'admin123', is_admin=True, is_friend=True),
    'Glory': User('Glory', 'lory', is_admin=False, is_friend=True)
}

@login_manager.user_loader
def load_user(user_id):
    return USERS.get(user_id)

# ============================================================
# ADMIN REQUIRED
# ============================================================
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You need admin access for this page.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# ============================================================
# ROUTES
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
        
        user = USERS.get(username)
        if user and user.check_password(password):
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

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', 
        questions=[],
        current_question=None,
        current_index=0,
        total_questions=0,
        is_admin=current_user.is_admin,
        is_friend=current_user.is_friend,
        current_user=current_user,
        feedback_questions=[],
        typing_text=None,
        show_typing=False,
        replies=[]
    )

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users_list = []
    for username, user in USERS.items():
        users_list.append({
            'username': username,
            'is_admin': user.is_admin,
            'is_friend': user.is_friend,
            'id': username,
            'created_at': datetime.now()
        })
    return render_template('admin_users.html', users=users_list)

@app.route('/admin/feedback')
@login_required
@admin_required
def admin_feedback():
    return render_template('admin_feedback.html', 
        questions=[],
        responses=[],
        feedback_questions=[]
    )

@app.route('/admin/responses')
@login_required
@admin_required
def admin_responses():
    return render_template('admin_responses.html',
        all_replies=[],
        total_replies=0,
        unique_questions=0,
        total_questions=0,
        completion_percentage=0
    )

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_settings():
    settings = {'site_title': 'YASH WORLD', 'site_tagline': 'Private Messaging Platform'}
    if request.method == 'POST':
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('admin_settings'))
    return render_template('admin_settings.html', settings=settings)

@app.route('/admin/typing-text', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_typing_text():
    if request.method == 'POST':
        flash('Typing text updated successfully!', 'success')
        return redirect(url_for('admin_typing_text'))
    
    return render_template('admin_typing_text.html', 
        typing_texts=[],
        active_text=None
    )

@app.route('/admin/typing-text/<int:text_id>/activate')
@login_required
@admin_required
def admin_activate_typing_text(text_id):
    flash('Typing text activated!', 'success')
    return redirect(url_for('admin_typing_text'))

@app.route('/admin/typing-text/<int:text_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_typing_text(text_id):
    flash('Typing text deleted!', 'success')
    return redirect(url_for('admin_typing_text'))

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
# RUN THE APPLICATION
# ============================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
