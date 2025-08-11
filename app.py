from flask import Flask, render_template, request, redirect, url_for, flash, session
import os, sqlite3, hashlib

# Database wrapper (your existing FaceRecognitionDatabase)
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
        # Core tables
        cur.execute("""
            CREATE TABLE IF NOT EXISTS persons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS camera_feeds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                rtsp_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER,
                camera_id INTEGER,
                triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                acknowledged INTEGER DEFAULT 0
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER,
                camera_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Users table
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

    def _exec(self, sql, params=()):
        conn = self.get_connection()
        conn.execute(sql, params)
        conn.commit()
        conn.close()

    def hash_password(self, pw): return hashlib.sha256(pw.encode()).hexdigest()

    def add_user(self, email, password, is_admin=False):
        h = self.hash_password(password)
        self._exec("INSERT INTO users(email,password_hash,is_admin) VALUES(?,?,?)",
                   (email, h, 1 if is_admin else 0))

    def check_user_access(self, email, password):
        conn = self.get_connection()
        row = conn.execute(
            "SELECT * FROM users WHERE email=? AND password_hash=?",
            (email, self.hash_password(password))
        ).fetchone()
        conn.close()
        return row is not None

    def is_admin(self, email):
        conn = self.get_connection()
        row = conn.execute("SELECT is_admin FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
        return row and row['is_admin']==1

    def get_all_users(self):
        conn = self.get_connection()
        rows = conn.execute(
            "SELECT id,email,is_admin,created_at FROM users ORDER BY created_at DESC"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_all_persons(self):
        conn = self.get_connection()
        rows = conn.execute("SELECT * FROM persons ORDER BY created_at DESC").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def add_person(self, name, description):
        self._exec("INSERT INTO persons(name,description) VALUES(?,?)", (name, description))

    def get_all_camera_feeds(self):
        conn = self.get_connection()
        rows = conn.execute("SELECT * FROM camera_feeds ORDER BY created_at DESC").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def add_camera(self, name, rtsp_url):
        self._exec("INSERT INTO camera_feeds(name,rtsp_url) VALUES(?,?)", (name, rtsp_url))

    def get_all_alerts(self):
        conn = self.get_connection()
        rows = conn.execute("SELECT * FROM alerts ORDER BY triggered_at DESC").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def acknowledge_alert(self, alert_id):
        self._exec("UPDATE alerts SET acknowledged=1 WHERE id=?", (alert_id,))

    def get_all_detections(self):
        conn = self.get_connection()
        rows = conn.execute("SELECT * FROM detections ORDER BY timestamp DESC").fetchall()
        conn.close()
        return [dict(r) for r in rows]

face_db = FaceRecognitionDatabase()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY','replace_with_secure_key')

# Authentication routes

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    error=None
    if request.method=='POST':
        e=request.form['email'].strip()
        p=request.form['password']
        if face_db.check_user_access(e,p):
            session['user_email']=e
            session['is_admin']=face_db.is_admin(e)
            return redirect(url_for('dashboard'))
        error='Invalid credentials'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Dashboard & management pages

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
        flash('Access denied'); return redirect(url_for('dashboard'))
    users=face_db.get_all_users()
    return render_template('manage_users.html', users=users)

@app.route('/persons', methods=['GET','POST'])
def persons():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    if request.method=='POST':
        face_db.add_person(request.form['name'], request.form['description'])
        return redirect(url_for('persons'))
    ps=face_db.get_all_persons()
    return render_template('persons.html', persons=ps)

@app.route('/camera_feeds', methods=['GET','POST'])
def camera_feeds():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    if request.method=='POST':
        face_db.add_camera(request.form['name'], request.form['rtsp_url'])
        return redirect(url_for('camera_feeds'))
    cf=face_db.get_all_camera_feeds()
    return render_template('camera_feeds.html', cameras=cf)

@app.route('/alerts')
def alerts():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    als=face_db.get_all_alerts()
    return render_template('alerts.html', alerts=als)

@app.route('/alerts/ack/<int:alert_id>')
def ack_alert(alert_id):
    face_db.acknowledge_alert(alert_id)
    return redirect(url_for('alerts'))

@app.route('/detections')
def detections():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    det=face_db.get_all_detections()
    return render_template('detections.html', detections=det)

if __name__=='__main__':
    app.run(debug=True)