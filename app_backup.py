from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from database import User  # Import your User model from database.py

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change to something secure

# --- Flask-Login setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect here if not logged in

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))  # Adjust if your User model differs

# --- Login route ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user and user.verify_password(password):  # Ensure verify_password exists
            login_user(user)
            return redirect(url_for('dashboard'))  # ✅ Redirect to dashboard
        else:
            error = "Invalid email or password"
            return render_template('login.html', error=error)

    return render_template('login.html')

# --- Dashboard route ---
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', username=current_user.email)

# --- Logout route ---
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
