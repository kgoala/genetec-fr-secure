from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import os
from database import FaceRecognitionDatabase

app = Flask(__name__)
app.secret_key = 'your-super-secret-key-change-this'
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = FaceRecognitionDatabase()

# Demo/AI mode state
ai_mode_active = False
demo_running = False
demo_stats = {'detections': 0, 'current_frame': 0, 'status': 'Stopped'}

ALLOWED_EXTENSIONS = {'png','jpg','jpeg','gif','mp4','avi','mov','mkv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1).lower() in ALLOWED_EXTENSIONS

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].lower().strip()
        password = request.form['password']
        
        if db.check_user_access(email, password):
            session['user_email'] = email
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password, or access not granted', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_email', None)
    return redirect(url_for('login'))

# Protected Routes
@app.route('/')
@login_required
def dashboard():
    stats = db.get_system_stats()
    return render_template('dashboard.html', stats=stats, ai_mode=ai_mode_active)

@app.route('/toggle_ai_mode', methods=['POST'])
@login_required
def toggle_ai_mode():
    global ai_mode_active
    ai_mode_active = not ai_mode_active
    return jsonify({'ai_mode': ai_mode_active})

@app.route('/persons')
@login_required
def persons():
    conn = db.get_connection()
    persons_list = [dict(row) for row in conn.execute('SELECT * FROM persons ORDER BY id DESC')]
    conn.close()
    return render_template('persons.html', persons=persons_list)

@app.route('/add_person', methods=['GET','POST'])
@login_required
def add_person():
    if request.method == 'POST':
        db.add_person(request.form['name'], request.form.get('description',''))
        for file in request.files.getlist('photos'):
            if file and allowed_file(file.filename):
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename)))
        flash("Person added successfully", "success")
        return redirect(url_for('persons'))
    return render_template('add_person.html')

@app.route('/cameras', methods=['GET','POST'])
@login_required
def cameras():
    if request.method == 'POST':
        db.add_camera(request.form['name'], request.form['rtsp_url'])
        flash("Camera added", "success")
    conn = db.get_connection()
    cams = [dict(row) for row in conn.execute('SELECT * FROM camera_feeds')]
    conn.close()
    return render_template('cameras.html', cameras=cams)

@app.route('/detections')
@login_required
def detections():
    conn = db.get_connection()
    dets = [dict(row) for row in conn.execute('SELECT * FROM detections ORDER BY timestamp DESC')]
    conn.close()
    return render_template('detections.html', detections=dets)

@app.route('/alerts', methods=['GET','POST'])
@login_required
def alerts():
    if request.method == 'POST' and 'acknowledge' in request.form:
        db.acknowledge_alert(int(request.form['acknowledge']))
        flash("Alert acknowledged!", "success")
        return redirect(url_for('alerts'))
    conn = db.get_connection()
    alerts_list = [dict(row) for row in conn.execute('SELECT * FROM alerts ORDER BY triggered_at DESC')]
    conn.close()
    return render_template('alerts.html', alerts=alerts_list)

@app.route('/reports')
@login_required
def reports():
    stats = db.get_system_stats()
    return render_template('reports.html', stats=stats)

@app.route('/settings', methods=['GET','POST'])
@login_required
def settings():
    if request.method == 'POST':
        flash("Settings updated", "success")
    return render_template('settings.html')

# User Management (Admin only)
@app.route('/manage_users', methods=['GET', 'POST'])
@login_required
def manage_users():
    # Check if current user is admin
    if not db.is_admin(session['user_email']):
        flash('Access denied - Admin only', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form['email'].lower().strip()
        password = request.form['password']
        is_admin = 'is_admin' in request.form
        db.add_user(email, password, is_admin)
        flash(f"User {email} added successfully", "success")
    
    users = db.get_all_users()
    return render_template('manage_users.html', users=users)

@app.route('/delete_user/<int:user_id>')
@login_required
def delete_user(user_id):
    if not db.is_admin(session['user_email']):
        flash('Access denied - Admin only', 'error')
        return redirect(url_for('dashboard'))
    
    db.delete_user(user_id)
    flash("User deleted", "success")
    return redirect(url_for('manage_users'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
