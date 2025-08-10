import sqlite3
import hashlib

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

        # Existing tables
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
        
        # New users table for access control
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
        
        # Create default admin user if no users exist
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            self.add_user('admin@genetec.com', 'admin123', True)
        
        conn.close()

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def add_user(self, email, password, is_admin=False):
        password_hash = self.hash_password(password)
        self._exec("INSERT INTO users (email, password_hash, is_admin) VALUES (?,?,?)", 
                  (email, password_hash, 1 if is_admin else 0))

    def check_user_access(self, email, password):
        conn = self.get_connection()
        password_hash = self.hash_password(password)
        user = conn.execute("SELECT * FROM users WHERE email=? AND password_hash=?", 
                           (email, password_hash)).fetchone()
        conn.close()
        return user is not None

    def is_admin(self, email):
        conn = self.get_connection()
        user = conn.execute("SELECT is_admin FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
        return user and user['is_admin'] == 1

    def get_all_users(self):
        conn = self.get_connection()
        users = [dict(row) for row in conn.execute("SELECT id, email, is_admin, created_at FROM users ORDER BY created_at DESC")]
        conn.close()
        return users

    def delete_user(self, user_id):
        self._exec("DELETE FROM users WHERE id=?", (user_id,))

    # Existing methods remain the same
    def add_person(self, name, description):
        self._exec("INSERT INTO persons (name, description) VALUES (?,?)", (name, description))

    def add_camera(self, name, rtsp_url):
        self._exec("INSERT INTO camera_feeds (name, rtsp_url) VALUES (?,?)", (name, rtsp_url))

    def add_alert(self, person_id, camera_id):
        self._exec("INSERT INTO alerts (person_id, camera_id) VALUES (?,?)", (person_id, camera_id))

    def acknowledge_alert(self, alert_id):
        self._exec("UPDATE alerts SET acknowledged=1 WHERE id=?", (alert_id,))

    def add_detection(self, person_id, camera_id):
        self._exec("INSERT INTO detections (person_id, camera_id) VALUES (?,?)", (person_id, camera_id))

    def _exec(self, sql, params=()):
        conn = self.get_connection()
        conn.execute(sql, params)
        conn.commit()
        conn.close()

    def get_system_stats(self):
        conn = self.get_connection()
        stats = {
            'total_persons': conn.execute("SELECT COUNT(*) FROM persons").fetchone()[0],
            'active_cameras': conn.execute("SELECT COUNT(*) FROM camera_feeds").fetchone(),
            'alerts': conn.execute("SELECT COUNT(*) FROM alerts").fetchone(),
            'detections': conn.execute("SELECT COUNT(*) FROM detections").fetchone()
        }
        conn.close()
        return stats
