from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import sqlite3
import hashlib

# --- Database wrapper from your existing database.py ---
class FaceRecognitionDatabase:
    def __init__(self, db_path='face_recognition.db'):
        self.db_path = db_path
        self._init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self.get_connection()
        cur = conn.cursor()
        # persons, camera_feeds, alerts, detections tables (omitted here for brevity)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            self.add_user('admin@genetec.com', 'admin123', True)
        conn.close()

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def add_user(self, email, password, is_admin=False):
        password_hash = self.hash_password(password)
        self._exec(
            "INSERT INTO users (email, password_hash, is_admin) VALUES (?,?,?)",
            (email, password_hash, 1 if is_admin else 0)
        )

    def check_user_access(self, email, password):
        conn = self.get_connection()
        ph = self.hash_password(password)
        user = conn.execute(
            "SELECT * FROM users WHERE email=? AND password_hash=?",
            (email, ph)
        ).fetchone()
        conn.close()
        return user is not None

    def is_admin(self, email):
        conn = self.get_connection()
        row = conn.execute(
            "SELECT is_admin FROM users WHERE email=?", (email,)
        ).fetchone()
        conn.close()
        return row and row['is_admin'] == 1

    def get_all_users(self):
        conn = self.get_connection()
        rows = conn.execute(
            "SELECT id, email, is_admin, created_at FROM users ORDER BY created_at DESC"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def _exec(self, sql, params=()):
        conn = self.get_connection()
        conn.execute(sql, params)
        conn.commit()
        conn.close()

# --- Flask app setup ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'replace_this_with_secure_key')

face_db = FaceRecognitionDatabase()

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        if face_db.check_user_access(email, password):
            session['user_email'] = email
            session['is_admin'] = face_db.is_admin(email)
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid email or password'
    return render_template('login.html', error=error)

@app.route('/dashboard')
def dashboard():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=session['user_email'])

@app.route('/manage_users')
def manage_users():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    if not session.get('is_admin'):
        flash('Access denied')
        return redirect(url_for('dashboard'))
    users = face_db.get_all_users()
    return render_template('manage_users.html', users=users)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
