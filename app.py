import os
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, abort, flash
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from utils.db import init_db, get_db_connection

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
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        doctor_id = request.form.get('doctor_id')

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        try:
            cursor.execute("INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                           (name, email, hashed_password, role))
            user_id = cursor.lastrowid

            if role == 'patient' and doctor_id:
                cursor.execute("INSERT INTO doctor_patients (doctor_id, patient_id) VALUES (%s, %s)",
                               (doctor_id, user_id))

            conn.commit()
        except mysql.connector.Error as err:
            cursor.close()
            conn.close()
            flash("Error: Email address already exists or database error occurred!", "danger")
            return redirect(url_for('register'))
        
        cursor.close()
        conn.close()
        return redirect(url_for('login'))

    cursor.execute("SELECT id, name, email FROM users WHERE role = 'doctor'")
    doctors = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('register.html', doctors=doctors)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
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
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()
    
    reports = []
    patients = []
    medications = []

    if user['role'] == 'patient':
        cursor.execute("SELECT * FROM reports WHERE patient_id = %s", (session['user_id'],))
        reports = cursor.fetchall()
        
        cursor.execute("SELECT * FROM medications WHERE patient_id = %s", (session['user_id'],))
        medications = cursor.fetchall()
    elif user['role'] == 'doctor':
        cursor.execute('''
            SELECT u.id, u.name, u.email FROM users u
            JOIN doctor_patients dp ON u.id = dp.patient_id
            WHERE dp.doctor_id = %s
        ''', (session['user_id'],))
        patients = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('dashboard.html', user=user, reports=reports, patients=patients, medications=medications)

@app.route('/doctor/patient/<int:patient_id>')
def view_patient_reports(patient_id):
    if 'user_id' not in session or session['role'] != 'doctor':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('''
        SELECT * FROM doctor_patients 
        WHERE doctor_id = %s AND patient_id = %s
    ''', (session['user_id'], patient_id))
    assignment = cursor.fetchone()

    if not assignment:
        cursor.close()
        conn.close()
        return abort(403)

    cursor.execute("SELECT * FROM users WHERE id = %s", (patient_id,))
    patient = cursor.fetchone()
    
    cursor.execute("SELECT * FROM reports WHERE patient_id = %s", (patient_id,))
    reports = cursor.fetchall()
    
    cursor.execute("SELECT * FROM medications WHERE patient_id = %s", (patient_id,))
    medications = cursor.fetchall()
    
    cursor.close()
    conn.close()

    return render_template('patient_reports.html', patient=patient, reports=reports, medications=medications)

@app.route('/doctor/prescribe/<int:patient_id>', methods=['POST'])
def prescribe_medication(patient_id):
    if 'user_id' not in session or session['role'] != 'doctor':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('''
        SELECT * FROM doctor_patients 
        WHERE doctor_id = %s AND patient_id = %s
    ''', (session['user_id'], patient_id))
    assignment = cursor.fetchone()

    if not assignment:
        cursor.close()
        conn.close()
        return abort(403)

    med_name = request.form['medication_name']
    dosage = request.form['dosage']
    instructions = request.form['instructions']

    cursor.execute('''
        INSERT INTO medications (patient_id, doctor_id, medication_name, dosage, instructions)
        VALUES (%s, %s, %s, %s, %s)
    ''', (patient_id, session['user_id'], med_name, dosage, instructions))
    conn.commit()
    
    cursor.close()
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
        cursor = conn.cursor()
        cursor.execute("INSERT INTO reports (patient_id, file_name) VALUES (%s, %s)",
                       (session['user_id'], unique_filename))
        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for('dashboard'))
    
    return "Invalid file type. Only PDF, PNG, JPG allowed."

@app.route('/view/<int:report_id>')
def view_report(report_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM reports WHERE id = %s", (report_id,))
    report = cursor.fetchone()
    
    if not report:
        cursor.close()
        conn.close()
        return abort(404)

    if session['role'] == 'doctor':
        cursor.execute('''
            SELECT * FROM doctor_patients 
            WHERE doctor_id = %s AND patient_id = %s
        ''', (session['user_id'], report['patient_id']))
        assignment = cursor.fetchone()
        if not assignment:
            cursor.close()
            conn.close()
            return abort(403)
    elif session['role'] == 'patient' and report['patient_id'] != session['user_id']:
        cursor.close()
        conn.close()
        return abort(403)

    cursor.close()
    conn.close()
    return send_from_directory(app.config['UPLOAD_FOLDER'], report['file_name'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
