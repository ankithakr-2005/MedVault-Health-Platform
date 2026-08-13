import os
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, abort, flash
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from utils.db import init_db, get_db_connection
sqlite3 = __import__('sqlite3')

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
bcrypt = Bcrypt(app)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    conn = get_db_connection()
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        doctor_id = request.form.get('doctor_id')

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                           (name, email, hashed_password, role))
            user_id = cursor.lastrowid

            if role == 'patient' and doctor_id:
                cursor.execute("INSERT INTO doctor_patients (doctor_id, patient_id) VALUES (?, ?)",
                               (doctor_id, user_id))

            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            flash("Error: Email address already exists!", "danger")
            return redirect(url_for('register'))
        
        conn.close()
        return redirect(url_for('login'))

    doctors = conn.execute("SELECT id, name, email FROM users WHERE role = 'doctor'").fetchall()
    conn.close()
    return render_template('register.html', doctors=doctors)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and bcrypt.check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password!", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    
    reports = []
    patients = []
    medications = []

    if user['role'] == 'patient':
        reports = conn.execute("SELECT * FROM reports WHERE patient_id = ?", (session['user_id'],)).fetchall()
        medications = conn.execute("SELECT * FROM medications WHERE patient_id = ?", (session['user_id'],)).fetchall()
    elif user['role'] == 'doctor':
        patients = conn.execute('''
            SELECT u.id, u.name, u.email FROM users u
            JOIN doctor_patients dp ON u.id = dp.patient_id
            WHERE dp.doctor_id = ?
        ''', (session['user_id'],)).fetchall()

    conn.close()
    return render_template('dashboard.html', user=user, reports=reports, patients=patients, medications=medications)

@app.route('/doctor/patient/<int:patient_id>')
def view_patient_reports(patient_id):
    if 'user_id' not in session or session['role'] != 'doctor':
        return redirect(url_for('login'))

    conn = get_db_connection()
    
    assignment = conn.execute('''
        SELECT * FROM doctor_patients 
        WHERE doctor_id = ? AND patient_id = ?
    ''', (session['user_id'], patient_id)).fetchone()

    if not assignment:
        conn.close()
        return abort(403)

    patient = conn.execute("SELECT * FROM users WHERE id = ?", (patient_id,)).fetchone()
    reports = conn.execute("SELECT * FROM reports WHERE patient_id = ?", (patient_id,)).fetchall()
    medications = conn.execute("SELECT * FROM medications WHERE patient_id = ?", (patient_id,)).fetchall()
    conn.close()

    return render_template('patient_reports.html', patient=patient, reports=reports, medications=medications)

@app.route('/doctor/prescribe/<int:patient_id>', methods=['POST'])
def prescribe_medication(patient_id):
    if 'user_id' not in session or session['role'] != 'doctor':
        return redirect(url_for('login'))

    conn = get_db_connection()
    
    assignment = conn.execute('''
        SELECT * FROM doctor_patients 
        WHERE doctor_id = ? AND patient_id = ?
    ''', (session['user_id'], patient_id)).fetchone()

    if not assignment:
        conn.close()
        return abort(403)

    med_name = request.form['medication_name']
    dosage = request.form['dosage']
    instructions = request.form['instructions']

    conn.execute('''
        INSERT INTO medications (patient_id, doctor_id, medication_name, dosage, instructions)
        VALUES (?, ?, ?, ?, ?)
    ''', (patient_id, session['user_id'], med_name, dosage, instructions))
    conn.commit()
    conn.close()

    return redirect(url_for('view_patient_reports', patient_id=patient_id))

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'user_id' not in session or session['role'] != 'patient':
        return redirect(url_for('login'))

    if 'report' not in request.files:
        return "No file part"
    
    file = request.files['report']
    if file.filename == '':
        return "No selected file"

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"user_{session['user_id']}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)

        conn = get_db_connection()
        conn.execute("INSERT INTO reports (patient_id, file_name) VALUES (?, ?)",
                     (session['user_id'], unique_filename))
        conn.commit()
        conn.close()

        return redirect(url_for('dashboard'))
    
    return "Invalid file type. Only PDF, PNG, JPG allowed."

@app.route('/view/<int:report_id>')
def view_report(report_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    report = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    
    if not report:
        conn.close()
        return abort(404)

    if session['role'] == 'doctor':
        assignment = conn.execute('''
            SELECT * FROM doctor_patients 
            WHERE doctor_id = ? AND patient_id = ?
        ''', (session['user_id'], report['patient_id'])).fetchone()
        if not assignment:
            conn.close()
            return abort(403)
    elif session['role'] == 'patient' and report['patient_id'] != session['user_id']:
        conn.close()
        return abort(403)

    conn.close()
    return send_from_directory(app.config['UPLOAD_FOLDER'], report['file_name'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)