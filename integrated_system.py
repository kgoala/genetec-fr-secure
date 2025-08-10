from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename
import os
from database import FaceRecognitionDatabase

app = Flask(__name__)
app.secret_key = 'your-secret-key'
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = FaceRecognitionDatabase()

# Demo/AI mode state
ai_mode_active = False
demo_running = False
demo_stats = {'detections': 0, 'current_frame': 0, 'status': 'Stopped'}

ALLOWED_EXTENSIONS = {'png','jpg','jpeg','gif','mp4','avi','mov','mkv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def dashboard():
    stats = db.get_system_stats()
    return render_template('dashboard.html', stats=stats, ai_mode=ai_mode_active)

@app.route('/toggle_ai_mode', methods=['POST'])
def toggle_ai_mode():
    global ai_mode_active
    ai_mode_active = not ai_mode_active
    return jsonify({'ai_mode': ai_mode_active})

@app.route('/persons')
def persons():
    conn = db.get_connection()
    persons_list = [dict(row) for row in conn.execute('SELECT * FROM persons ORDER BY id DESC')]
    conn.close()
    return render_template('persons.html', persons=persons_list)

@app.route('/add_person', methods=['GET','POST'])
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
def cameras():
    if request.method == 'POST':
        db.add_camera(request.form['name'], request.form['rtsp_url'])
        flash("Camera added", "success")
    conn = db.get_connection()
    cams = [dict(row) for row in conn.execute('SELECT * FROM camera_feeds')]
    conn.close()
    return render_template('cameras.html', cameras=cams)

@app.route('/detections')
def detections():
    conn = db.get_connection()
    dets = [dict(row) for row in conn.execute('SELECT * FROM detections ORDER BY timestamp DESC')]
    conn.close()
    return render_template('detections.html', detections=dets)

@app.route('/alerts', methods=['GET','POST'])
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
def reports():
    stats = db.get_system_stats()
    return render_template('reports.html', stats=stats)

@app.route('/settings', methods=['GET','POST'])
def settings():
    if request.method == 'POST':
        flash("Settings updated", "success")
    return render_template('settings.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
