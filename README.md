
# MedVault - Digital Health Records Platform

A secure, full-stack digital health records web application built with **Python, Flask, SQLite, and Bootstrap**, featuring role-based access control (RBAC), secure file uploads, and encrypted authentication.

## Key Features
* **Secure Authentication:** User registration and login utilizing `Flask-Bcrypt` for password hashing and secure server-side session management.
* **Role-Based Access Control (RBAC):** Distinct workflows and dashboard views tailored for **Patients** and **Doctors**.
* **Relational Database Design:** Features a Many-to-Many junction table (`doctor_patients`) ensuring strict data isolation—doctors can only view medical records and manage prescriptions for patients explicitly assigned to their roster.
* **Secure File Handling:** Patients can upload medical scans and reports (`.pdf`, `.jpg`, `.png`) with backend extension verification and safe filename sanitization via Werkzeug to prevent path traversal vulnerabilities.
* **Prescription Management:** Doctors can issue digital prescriptions and medications tied directly to individual patient profiles.

## System Architecture & Flow
1. **Authentication Layer:** Users register/login with hashed credentials managed through secure server sessions.
2. **Access Control:** 
   * **Patients** can upload medical reports and view doctor-prescribed medications.
   * **Doctors** view exclusively mapped patient rosters via the Many-to-Many junction table.
3. **Security Pipeline:** File uploads undergo backend extension whitelisting and filename sanitization.

## Tech Stack
* **Backend:** Python, Flask, Flask-Bcrypt, Werkzeug
* **Database:** SQLite (Relational Schema with Custom Junction Tables)
* **Frontend:** HTML5, CSS3, Bootstrap 5, Jinja2 Templates
