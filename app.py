from flask import Flask, render_template, request, redirect, url_for, session 
from database import FaceRecognitionDatabase 
 
app = Flask(__name__) 
app.config['SECRET_KEY'] = 'your_secret_key_here' 
face_db = FaceRecognitionDatabase() 
 
@app.route('/') 
def index(): 
    return redirect(url_for('login')) 
 
@app.route('/login', methods=['GET', 'POST']) 
def login(): 
    if request.method == 'POST': 
        email = request.form.get('email') 
        password = request.form.get('password') 
        if face_db.check_user_access(email, password): 
            session['user_email'] = email 
            return redirect(url_for('dashboard')) 
        else: 
            return render_template('login.html', error='Invalid credentials') 
    return render_template('login.html') 
 
@app.route('/dashboard') 
def dashboard(): 
    if 'user_email' not in session: 
        return redirect(url_for('login')) 
    return render_template('dashboard.html', username=session['user_email']) 
 
@app.route('/logout') 
def logout(): 
    session.clear() 
    return redirect(url_for('login')) 
 
if __name__ == '__main__': 
    app.run(debug=True) 
