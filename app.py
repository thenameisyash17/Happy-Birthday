# ============================================================
# YASH WORLD - Private Messaging & QA Platform
# Vercel & Render Compatible Version
# ============================================================

import os
import logging
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import base64

# ============================================================
# LOGGING CONFIGURATION
# ============================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# APP CREATION
# ============================================================
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'yash-world-secret-key-2024')

# ============================================================
# DATABASE CONFIGURATION
# ============================================================
DATABASE_URL = os.environ.get('DATABASE_URL')

# For Vercel, use SQLite (read-only) or skip DB operations
IS_VERCEL = os.environ.get('VERCEL', False)

if DATABASE_URL and not IS_VERCEL:
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    logger.info("✅ PostgreSQL database configured")
elif IS_VERCEL:
    # On Vercel, use in-memory SQLite for basic functionality
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    logger.warning("⚠️ Using in-memory SQLite on Vercel - data will not persist")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yash_world.db'
    logger.warning("⚠️ SQLite database configured")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
    'pool_size': 5,
    'max_overflow': 10
}

# ============================================================
# DATABASE INITIALIZATION
# ============================================================
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ============================================================
# MODELS
# ============================================================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_friend = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    questions = db.relationship('Question', backref='asker', lazy=True)
    replies = db.relationship('Reply', backref='replier', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class TypingText(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    
    image_data = db.Column(db.Text)
    video_data = db.Column(db.Text)
    audio_data = db.Column(db.Text)
    image_filename = db.Column(db.String(200))
    video_filename = db.Column(db.String(200))
    audio_filename = db.Column(db.String(200))
    
    answer_text = db.Column(db.Text)
    answer_image_data = db.Column(db.Text)
    answer_video_data = db.Column(db.Text)
    answer_audio_data = db.Column(db.Text)
    answer_image_filename = db.Column(db.String(200))
    answer_video_filename = db.Column(db.String(200))
    answer_audio_filename = db.Column(db.String(200))
    has_answer = db.Column(db.Boolean, default=False)
    
    is_answered = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    replies = db.relationship('Reply', backref='question', cascade='all, delete-orphan', lazy=True)

class Reply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    
    image_data = db.Column(db.Text)
    video_data = db.Column(db.Text)
    audio_data = db.Column(db.Text)
    image_filename = db.Column(db.String(200))
    video_filename = db.Column(db.String(200))
    audio_filename = db.Column(db.String(200))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class FeedbackQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(500), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class FeedbackResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('feedback_question.id', ondelete='CASCADE'), nullable=False)
    rating = db.Column(db.Integer)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='feedback_responses', lazy=True)
    question = db.relationship('FeedbackQuestion', backref='responses', lazy=True)

class SiteSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    site_title = db.Column(db.String(200), default='YASH WORLD')
    site_tagline = db.Column(db.String(200), default='Private Messaging Platform')
    welcome_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ============================================================
# LOGIN MANAGER
# ============================================================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You need admin access for this page.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# ============================================================
# CONTEXT PROCESSOR
# ============================================================

@app.context_processor
def utility_processor():
    def get_site_settings():
        settings = SiteSettings.query.first()
        if not settings:
            settings = SiteSettings()
            db.session.add(settings)
            db.session.commit()
        return settings
    return dict(get_site_settings=get_site_settings)

# ============================================================
# MEDIA HELPERS
# ============================================================

ALLOWED_IMAGES = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_VIDEOS = {'mp4', 'webm', 'mov', 'avi', 'mkv'}
ALLOWED_AUDIO = {'mp3', 'wav', 'ogg', 'm4a', 'aac', 'flac'}

def get_file_extension(filename):
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

def is_allowed_image(filename):
    return get_file_extension(filename) in ALLOWED_IMAGES

def is_allowed_video(filename):
    return get_file_extension(filename) in ALLOWED_VIDEOS

def is_allowed_audio(filename):
    return get_file_extension(filename) in ALLOWED_AUDIO

def file_to_base64(file):
    if file and file.filename:
        try:
            file_data = file.read()
            base64_data = base64.b64encode(file_data).decode('utf-8')
            return base64_data
        except Exception as e:
            logger.error(f"Error converting file to base64: {e}")
            return None
    return None

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
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()
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
# ROUTES - DASHBOARD
# ============================================================

@app.route('/dashboard')
@login_required
def dashboard():
    questions = Question.query.order_by(Question.created_at.asc()).all()
    is_admin = current_user.is_admin
    is_friend = current_user.is_friend
    
    typing_text = None
    show_typing = False
    
    if is_friend and not is_admin:
        typing_text = TypingText.query.filter_by(is_active=True).first()
        seen_typing = session.get('seen_typing_' + str(current_user.id), False)
        if typing_text and not seen_typing:
            show_typing = True
    
    current_index = session.get('current_question_index', 0)
    
    if not questions:
        return render_template('dashboard.html', 
            questions=[],
            current_question=None,
            current_index=0,
            total_questions=0,
            is_admin=is_admin,
            is_friend=is_friend,
            current_user=current_user,
            feedback_questions=[],
            typing_text=typing_text,
            show_typing=show_typing
        )
    
    if current_index >= len(questions):
        current_index = 0
        session['current_question_index'] = 0
    
    current_question = questions[current_index]
    total_questions = len(questions)
    
    replies = Reply.query.filter_by(question_id=current_question.id).order_by(Reply.created_at.asc()).all()
    
    feedback_questions = []
    if is_friend:
        feedback_questions = FeedbackQuestion.query.filter_by(is_active=True).all()
    
    return render_template('dashboard.html', 
        questions=questions,
        current_question=current_question,
        current_index=current_index,
        total_questions=total_questions,
        replies=replies,
        is_admin=is_admin,
        is_friend=is_friend,
        current_user=current_user,
        feedback_questions=feedback_questions,
        typing_text=typing_text,
        show_typing=show_typing
    )

# ============================================================
# ROUTES - NAVIGATE QUESTIONS
# ============================================================

@app.route('/navigate-question', methods=['POST'])
@login_required
def navigate_question():
    direction = request.form.get('direction')
    current_index = session.get('current_question_index', 0)
    total_questions = Question.query.count()
    
    if direction == 'next':
        current_index = min(current_index + 1, total_questions - 1)
    elif direction == 'prev':
        current_index = max(current_index - 1, 0)
    
    session['current_question_index'] = current_index
    return redirect(url_for('dashboard'))

# ============================================================
# ROUTES - SEEN TYPING
# ============================================================

@app.route('/seen-typing', methods=['POST'])
@login_required
def seen_typing():
    session['seen_typing_' + str(current_user.id)] = True
    return jsonify({'success': True})

# ============================================================
# ROUTES - ASK QUESTION
# ============================================================

@app.route('/ask', methods=['GET', 'POST'])
@login_required
def ask_question():
    if not current_user.is_admin:
        flash('Only admin can ask questions.', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        text = request.form.get('text', '').strip()
        
        if not text:
            flash('Please enter a question.', 'danger')
            return redirect(url_for('ask_question'))
        
        question = Question(
            user_id=current_user.id,
            text=text
        )
        
        if 'image' in request.files and request.files['image'].filename:
            file = request.files['image']
            if is_allowed_image(file.filename):
                question.image_data = file_to_base64(file)
                question.image_filename = secure_filename(file.filename)
        
        if 'video' in request.files and request.files['video'].filename:
            file = request.files['video']
            if is_allowed_video(file.filename):
                question.video_data = file_to_base64(file)
                question.video_filename = secure_filename(file.filename)
        
        if 'audio' in request.files and request.files['audio'].filename:
            file = request.files['audio']
            if is_allowed_audio(file.filename):
                question.audio_data = file_to_base64(file)
                question.audio_filename = secure_filename(file.filename)
        
        answer_text = request.form.get('answer_text', '').strip()
        if answer_text:
            question.answer_text = answer_text
            question.has_answer = True
            question.is_answered = True
            
            if 'answer_image' in request.files and request.files['answer_image'].filename:
                file = request.files['answer_image']
                if is_allowed_image(file.filename):
                    question.answer_image_data = file_to_base64(file)
                    question.answer_image_filename = secure_filename(file.filename)
            
            if 'answer_video' in request.files and request.files['answer_video'].filename:
                file = request.files['answer_video']
                if is_allowed_video(file.filename):
                    question.answer_video_data = file_to_base64(file)
                    question.answer_video_filename = secure_filename(file.filename)
            
            if 'answer_audio' in request.files and request.files['answer_audio'].filename:
                file = request.files['answer_audio']
                if is_allowed_audio(file.filename):
                    question.answer_audio_data = file_to_base64(file)
                    question.answer_audio_filename = secure_filename(file.filename)
        
        db.session.add(question)
        db.session.commit()
        
        flash('Question asked successfully!' + (' Answer added!' if answer_text else ''), 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('ask.html')

# ============================================================
# ROUTES - REPLY TO QUESTION
# ============================================================

@app.route('/reply/<int:question_id>', methods=['GET', 'POST'])
@login_required
def reply_question(question_id):
    question = Question.query.get_or_404(question_id)
    
    if not current_user.is_friend and not current_user.is_admin:
        flash('Only friend can reply.', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        text = request.form.get('text', '').strip()
        
        if not text:
            flash('Please enter a reply.', 'danger')
            return redirect(url_for('reply_question', question_id=question_id))
        
        reply = Reply(
            question_id=question_id,
            user_id=current_user.id,
            text=text
        )
        
        if 'image' in request.files and request.files['image'].filename:
            file = request.files['image']
            if is_allowed_image(file.filename):
                reply.image_data = file_to_base64(file)
                reply.image_filename = secure_filename(file.filename)
        
        if 'video' in request.files and request.files['video'].filename:
            file = request.files['video']
            if is_allowed_video(file.filename):
                reply.video_data = file_to_base64(file)
                reply.video_filename = secure_filename(file.filename)
        
        if 'audio' in request.files and request.files['audio'].filename:
            file = request.files['audio']
            if is_allowed_audio(file.filename):
                reply.audio_data = file_to_base64(file)
                reply.audio_filename = secure_filename(file.filename)
        
        db.session.add(reply)
        question.is_answered = True
        db.session.commit()
        
        flash('Reply sent successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('reply.html', question=question)

# ============================================================
# ROUTES - DELETE
# ============================================================

@app.route('/question/<int:question_id>/delete', methods=['POST'])
@login_required
def delete_question(question_id):
    if not current_user.is_admin:
        flash('Only admin can delete questions.', 'danger')
        return redirect(url_for('dashboard'))
    
    question = Question.query.get_or_404(question_id)
    db.session.delete(question)
    db.session.commit()
    flash('Question deleted successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/reply/<int:reply_id>/delete', methods=['POST'])
@login_required
def delete_reply(reply_id):
    if not current_user.is_admin:
        flash('Only admin can delete replies.', 'danger')
        return redirect(url_for('dashboard'))
    
    reply = Reply.query.get_or_404(reply_id)
    db.session.delete(reply)
    db.session.commit()
    flash('Reply deleted successfully!', 'success')
    return redirect(url_for('dashboard'))

# ============================================================
# ROUTES - EDIT QUESTION
# ============================================================

@app.route('/question/<int:question_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_question(question_id):
    question = Question.query.get_or_404(question_id)
    
    if request.method == 'POST':
        new_text = request.form.get('text', '').strip()
        if new_text:
            question.text = new_text
        
        new_answer = request.form.get('answer_text', '').strip()
        if new_answer:
            question.answer_text = new_answer
            question.has_answer = True
            question.is_answered = True
        
        db.session.commit()
        flash('Question updated successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('edit_question.html', question=question)

# ============================================================
# ROUTES - DELETE INDIVIDUAL MEDIA
# ============================================================

@app.route('/question/<int:question_id>/delete-media', methods=['POST'])
@login_required
@admin_required
def delete_question_media(question_id):
    question = Question.query.get_or_404(question_id)
    media_type = request.form.get('media_type')
    
    if media_type == 'image':
        question.image_data = None
        question.image_filename = None
        flash('Image deleted successfully!', 'success')
    elif media_type == 'video':
        question.video_data = None
        question.video_filename = None
        flash('Video deleted successfully!', 'success')
    elif media_type == 'audio':
        question.audio_data = None
        question.audio_filename = None
        flash('Audio deleted successfully!', 'success')
    elif media_type == 'answer_image':
        question.answer_image_data = None
        question.answer_image_filename = None
        flash('Answer image deleted successfully!', 'success')
    elif media_type == 'answer_video':
        question.answer_video_data = None
        question.answer_video_filename = None
        flash('Answer video deleted successfully!', 'success')
    elif media_type == 'answer_audio':
        question.answer_audio_data = None
        question.answer_audio_filename = None
        flash('Answer audio deleted successfully!', 'success')
    else:
        flash('Invalid media type.', 'danger')
        return redirect(url_for('edit_question', question_id=question_id))
    
    db.session.commit()
    return redirect(url_for('edit_question', question_id=question_id))

# ============================================================
# ROUTES - TYPING TEXT ADMIN
# ============================================================

@app.route('/admin/typing-text', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_typing_text():
    if request.method == 'POST':
        text = request.form.get('typing_text', '').strip()
        if text:
            TypingText.query.update({TypingText.is_active: False})
            new_text = TypingText(text=text, is_active=True)
            db.session.add(new_text)
            db.session.commit()
            flash('Typing text updated successfully!', 'success')
        else:
            flash('Please enter some text.', 'danger')
        return redirect(url_for('admin_typing_text'))
    
    typing_texts = TypingText.query.order_by(TypingText.created_at.desc()).all()
    active_text = TypingText.query.filter_by(is_active=True).first()
    
    return render_template('admin_typing_text.html', 
        typing_texts=typing_texts,
        active_text=active_text
    )

@app.route('/admin/typing-text/<int:text_id>/activate')
@login_required
@admin_required
def admin_activate_typing_text(text_id):
    TypingText.query.update({TypingText.is_active: False})
    text = TypingText.query.get_or_404(text_id)
    text.is_active = True
    db.session.commit()
    flash('Typing text activated!', 'success')
    return redirect(url_for('admin_typing_text'))

@app.route('/admin/typing-text/<int:text_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_typing_text(text_id):
    text = TypingText.query.get_or_404(text_id)
    db.session.delete(text)
    db.session.commit()
    flash('Typing text deleted!', 'success')
    return redirect(url_for('admin_typing_text'))

# ============================================================
# ROUTES - FEEDBACK SYSTEM
# ============================================================

@app.route('/admin/feedback', methods=['GET'])
@login_required
@admin_required
def admin_feedback():
    questions = FeedbackQuestion.query.order_by(FeedbackQuestion.created_at.desc()).all()
    responses = FeedbackResponse.query.order_by(FeedbackResponse.created_at.desc()).all()
    
    return render_template('admin_feedback.html', 
        questions=questions,
        responses=responses
    )

@app.route('/admin/feedback/add', methods=['POST'])
@login_required
@admin_required
def add_feedback_question():
    question_text = request.form.get('question', '').strip()
    if question_text:
        new_question = FeedbackQuestion(question=question_text)
        db.session.add(new_question)
        db.session.commit()
        flash('Feedback question added successfully!', 'success')
    else:
        flash('Please enter a question.', 'danger')
    return redirect(url_for('admin_feedback'))

@app.route('/admin/feedback/toggle/<int:q_id>', methods=['POST'])
@login_required
@admin_required
def toggle_feedback_question(q_id):
    question = FeedbackQuestion.query.get_or_404(q_id)
    question.is_active = not question.is_active
    db.session.commit()
    status = 'activated' if question.is_active else 'deactivated'
    flash(f'Feedback question {status}!', 'success')
    return redirect(url_for('admin_feedback'))

@app.route('/admin/feedback/delete/<int:q_id>', methods=['POST'])
@login_required
@admin_required
def delete_feedback_question(q_id):
    question = FeedbackQuestion.query.get_or_404(q_id)
    db.session.delete(question)
    db.session.commit()
    flash('Feedback question deleted!', 'success')
    return redirect(url_for('admin_feedback'))

@app.route('/submit-feedback', methods=['POST'])
@login_required
def submit_feedback():
    if not current_user.is_friend:
        flash('Only friends can submit feedback.', 'danger')
        return redirect(url_for('dashboard'))
    
    existing = FeedbackResponse.query.filter_by(user_id=current_user.id).first()
    if existing:
        flash('You have already submitted feedback.', 'warning')
        return redirect(url_for('dashboard'))
    
    question_ids = request.form.getlist('question_id')
    comment = request.form.get('comment', '').strip()
    
    saved_count = 0
    for q_id in question_ids:
        rating_key = f'rating_{q_id}'
        rating_value = request.form.get(rating_key)
        
        if q_id and rating_value:
            try:
                rating = int(rating_value)
                if rating > 0:
                    response = FeedbackResponse(
                        user_id=current_user.id,
                        question_id=int(q_id),
                        rating=rating,
                        comment=comment if comment else None
                    )
                    db.session.add(response)
                    saved_count += 1
            except ValueError:
                pass
    
    if saved_count > 0:
        db.session.commit()
        flash(f'Thank you for your feedback! 🌟 ({saved_count} responses saved)', 'success')
    else:
        flash('No ratings were submitted. Please try again.', 'danger')
    
    return redirect(url_for('dashboard'))

# ============================================================
# ROUTES - ADMIN RESPONSES
# ============================================================

@app.route('/admin/responses')
@login_required
@admin_required
def admin_responses():
    all_replies = Reply.query.order_by(Reply.created_at.desc()).all()
    total_questions = Question.query.count()
    unique_questions = db.session.query(Reply.question_id).distinct().count()
    
    completion_percentage = 0
    if total_questions > 0:
        completion_percentage = int((unique_questions / total_questions) * 100)
    
    return render_template('admin_responses.html',
        all_replies=all_replies,
        total_replies=len(all_replies),
        unique_questions=unique_questions,
        total_questions=total_questions,
        completion_percentage=completion_percentage
    )

# ============================================================
# ROUTES - ADMIN USERS
# ============================================================

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/user/<int:user_id>/toggle-friend', methods=['POST'])
@login_required
@admin_required
def toggle_friend(user_id):
    user = User.query.get_or_404(user_id)
    user.is_friend = not user.is_friend
    db.session.commit()
    status = 'enabled' if user.is_friend else 'disabled'
    flash(f'Friend access {status} for {user.username}', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<int:user_id>/reset-typing', methods=['POST'])
@login_required
@admin_required
def reset_typing(user_id):
    session.pop('seen_typing_' + str(user_id), None)
    flash('Typing animation reset for user.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_settings():
    settings = SiteSettings.query.first()
    if not settings:
        settings = SiteSettings()
        db.session.add(settings)
        db.session.commit()
    
    if request.method == 'POST':
        settings.site_title = request.form.get('site_title', 'YASH WORLD')
        settings.site_tagline = request.form.get('site_tagline', 'Private Messaging Platform')
        settings.welcome_message = request.form.get('welcome_message', '')
        db.session.commit()
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('admin_settings'))
    
    return render_template('admin_settings.html', settings=settings)

# ============================================================
# ROUTES - MEDIA SERVE
# ============================================================

@app.route('/media/question/image/<int:question_id>')
def question_image(question_id):
    question = Question.query.get_or_404(question_id)
    if question.image_data:
        return question.image_data, 200, {'Content-Type': 'image/jpeg'}
    return '', 404

@app.route('/media/question/video/<int:question_id>')
def question_video(question_id):
    question = Question.query.get_or_404(question_id)
    if question.video_data:
        return question.video_data, 200, {'Content-Type': 'video/mp4'}
    return '', 404

@app.route('/media/question/audio/<int:question_id>')
def question_audio(question_id):
    question = Question.query.get_or_404(question_id)
    if question.audio_data:
        return question.audio_data, 200, {'Content-Type': 'audio/mpeg'}
    return '', 404

@app.route('/media/reply/image/<int:reply_id>')
def reply_image(reply_id):
    reply = Reply.query.get_or_404(reply_id)
    if reply.image_data:
        return reply.image_data, 200, {'Content-Type': 'image/jpeg'}
    return '', 404

@app.route('/media/reply/video/<int:reply_id>')
def reply_video(reply_id):
    reply = Reply.query.get_or_404(reply_id)
    if reply.video_data:
        return reply.video_data, 200, {'Content-Type': 'video/mp4'}
    return '', 404

@app.route('/media/reply/audio/<int:reply_id>')
def reply_audio(reply_id):
    reply = Reply.query.get_or_404(reply_id)
    if reply.audio_data:
        return reply.audio_data, 200, {'Content-Type': 'audio/mpeg'}
    return '', 404

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
# DATABASE INITIALIZATION (SKIP ON VERCEL)
# ============================================================

ADMIN_USERNAME = "yash"
ADMIN_PASSWORD = "admin123"
FRIEND_USERNAME = "Glory"
FRIEND_PASSWORD = "lory"

def init_db():
    with app.app_context():
        try:
            db.create_all()
            logger.info("✅ Database tables created/verified")
            
            admin = User.query.filter_by(username=ADMIN_USERNAME).first()
            if not admin:
                admin = User(username=ADMIN_USERNAME, is_admin=True, is_friend=True)
                admin.set_password(ADMIN_PASSWORD)
                db.session.add(admin)
                db.session.commit()
                logger.info(f"✅ Admin user created: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")
            
            friend = User.query.filter_by(username=FRIEND_USERNAME).first()
            if not friend:
                friend = User(username=FRIEND_USERNAME, is_admin=False, is_friend=True)
                friend.set_password(FRIEND_PASSWORD)
                db.session.add(friend)
                db.session.commit()
                logger.info(f"✅ Friend user created: {FRIEND_USERNAME} / {FRIEND_PASSWORD}")
            
            settings = SiteSettings.query.first()
            if not settings:
                settings = SiteSettings(
                    site_title='YASH WORLD',
                    site_tagline='Private Messaging & QA Platform'
                )
                db.session.add(settings)
                db.session.commit()
                logger.info("✅ Default settings created")
            
            if FeedbackQuestion.query.count() == 0:
                default_questions = [
                    "How would you rate me as a friend?",
                    "How caring am I?",
                    "How supportive am I?",
                    "How trustworthy am I?",
                    "How loyal am I?",
                    "Would you recommend me as a friend?"
                ]
                for q in default_questions:
                    fq = FeedbackQuestion(question=q, is_active=True)
                    db.session.add(fq)
                db.session.commit()
                logger.info("✅ Default feedback questions created")
            
        except Exception as e:
            logger.error(f"❌ Database initialization error: {e}")
            db.session.rollback()

# Only initialize database if NOT on Vercel
if not os.environ.get('VERCEL'):
    init_db()

# ============================================================
# RUN THE APPLICATION
# ============================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
