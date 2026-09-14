import mysql.connector

# Default XAMPP MySQL configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  # XAMPP default root password is empty
    'database': 'medvault'
}

def get_db_connection():
    conn = mysql.connector.connect(**DB_CONFIG)
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL DEFAULT 'patient'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INT AUTO_INCREMENT PRIMARY KEY,
            patient_id INT,
            file_name VARCHAR(255) NOT NULL,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doctor_patients (
            id INT AUTO_INCREMENT PRIMARY KEY,
            doctor_id INT,
            patient_id INT,
            FOREIGN KEY (doctor_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (patient_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS medications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            patient_id INT,
            doctor_id INT,
            medication_name VARCHAR(255) NOT NULL,
            dosage VARCHAR(255) NOT NULL,
            instructions TEXT,
            prescribed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (doctor_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    cursor.close()
    conn.close()