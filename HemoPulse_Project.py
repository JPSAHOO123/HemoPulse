"""
=============================================================================
HEMOPULSE - PRECISION EMERGENCY BLOOD VAULT ENGINE (2026)
Backend Architecture: Python Flask + SQLite + FIFO Inventory Protocol
=============================================================================
"""

import sqlite3
import os
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

app = Flask(__name__)
app.secret_key = "hemopulse_precision_vault_secret_key_2026"
DB_NAME = "hemopulse.db"

# Component Shelf Life Matrix (in Days)
SHELF_LIFE = {
    "Whole Blood": 35,
    "Packed Red Blood Cells (RBC)": 42,
    "Platelets": 5,
    "Fresh Frozen Plasma (FFP)": 365
}

# 30 Odisha Districts Seed List
ODISHA_DISTRICTS = [
    "Angul", "Balangir", "Balasore", "Bargarh", "Bhadrak", "Boudh",
    "Cuttack", "Deogarh", "Dhenkanal", "Gajapati", "Ganjam", "Jagatsinghpur",
    "Jajpur", "Jharsuguda", "Kalahandi", "Kandhamal", "Kendrapara",
    "Kendujhar", "Khordha", "Koraput", "Malkangiri", "Mayurbhanj",
    "Nabarangpur", "Nayagarh", "Nuapada", "Puri", "Rayagada",
    "Sambalpur", "Subarnapur", "Sundargarh"
]


# =============================================================================
# DATABASE INITIALIZATION & SEEDING
# =============================================================================

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # 1. Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            blood_group TEXT DEFAULT 'Not Set',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. Hospitals Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hospitals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hospital_name TEXT NOT NULL,
            state TEXT NOT NULL,
            district TEXT NOT NULL,
            contact_number TEXT
        )
    ''')

    # 3. Inventory / FIFO Vault Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            blood_group TEXT NOT NULL,
            component_type TEXT NOT NULL,
            units INTEGER NOT NULL,
            donated_date TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            status TEXT DEFAULT 'ACTIVE'
        )
    ''')

    # 4. Immutable Transaction Ledger Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            txn_type TEXT NOT NULL,
            person_name TEXT NOT NULL,
            blood_group TEXT NOT NULL,
            component_type TEXT NOT NULL,
            units INTEGER NOT NULL,
            hospital_id INTEGER,
            timestamp TEXT NOT NULL
        )
    ''')

    # 5. User Donations Log Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS donations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name TEXT NOT NULL,
            user_email TEXT NOT NULL,
            blood_group TEXT NOT NULL,
            component_type TEXT NOT NULL,
            units INTEGER NOT NULL,
            donation_date TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            medical_condition TEXT NOT NULL,
            status TEXT DEFAULT 'APPROVED'
        )
    ''')

    # Seed 30 Districts of Odisha if Hospitals table is empty
    cursor.execute("SELECT COUNT(*) FROM hospitals")
    if cursor.fetchone()[0] == 0:
        sample_nodes = []
        for dist in ODISHA_DISTRICTS:
            sample_nodes.append((f"District Headquarters Hospital (DHH) {dist}", "Odisha", dist, "1800-889-7853"))
            sample_nodes.append((f"Sub-Divisional Medical Care Unit {dist}", "Odisha", dist, "0674-2391980"))
        
        # Premier Medical Hubs
        sample_nodes.extend([
            ("AIIMS Bhubaneswar Emergency ICU", "Odisha", "Khordha", "0674-2476789"),
            ("SCB Medical College & Hospital", "Odisha", "Cuttack", "0671-2414080"),
            ("MKCG Medical College & Hospital", "Odisha", "Ganjam", "0680-2292746"),
            ("VIMSAR Multi-Speciality Medical Hub", "Odisha", "Sambalpur", "0663-2430061")
        ])
        
        cursor.executemany(
            "INSERT INTO hospitals (hospital_name, state, district, contact_number) VALUES (?, ?, ?, ?)",
            sample_nodes
        )

    conn.commit()
    conn.close()


def update_expired_inventory():
    """Identifies and transitions active blood batches that have passed expiry."""
    today_str = datetime.now().strftime('%Y-%m-%d')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE inventory 
        SET status = 'EXPIRED' 
        WHERE status = 'ACTIVE' AND date(expiry_date) < date(?)
    """, (today_str,))
    conn.commit()
    conn.close()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please login to access your verified dashboard.", "info")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# =============================================================================
# APPLICATION ROUTES
# =============================================================================

@app.route('/')
def index():
    return render_template('index.html')


# --- 1. CONNECT HOSPITALS (B2B LOCATOR WITH ALPHABETICAL SORTING) ---
@app.route('/connect-hospitals')
def connect_hospitals():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT state FROM hospitals ORDER BY state ASC")
    states = [row['state'] for row in cursor.fetchall()]
    conn.close()
    return render_template('connect_hospitals.html', states=states)


@app.route('/api/get-districts/<path:state>')
def api_get_districts(state):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT district FROM hospitals WHERE state = ? ORDER BY district ASC", (state,))
    districts = [row['district'] for row in cursor.fetchall()]
    conn.close()
    return jsonify(districts)


@app.route('/api/get-hospitals/<path:state>/<path:district>')
def api_get_hospitals(state, district):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, hospital_name, district, state FROM hospitals WHERE state = ? AND district = ? ORDER BY hospital_name ASC",
        (state, district)
    )
    hospitals = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(hospitals)


# --- 2. DONATE BLOOD (VOLUNTARY VAULTING) ---
@app.route('/donate', methods=['GET', 'POST'])
def donate():
    if request.method == 'POST':
        blood_group = request.form.get('blood_group')
        component_type = request.form.get('component_type')
        units = int(request.form.get('units', 1))
        medical_condition = request.form.get('medical_condition')

        # Auto-Reject Safety Screening
        if medical_condition in ["HIV / AIDS", "Hepatitis B / C", "Mild Fever"]:
            flash(f"Medical Safety Screening: Donation auto-rejected due to condition ({medical_condition}). Recipient safety protocol applied.", "danger")
            return redirect(url_for('donate'))

        now = datetime.now()
        donation_date = now.strftime('%Y-%m-%d')
        days_valid = SHELF_LIFE.get(component_type, 35)
        expiry_date = (now + timedelta(days=days_valid)).strftime('%Y-%m-%d')
        timestamp_str = now.strftime('%Y-%m-%d %H:%M:%S')

        donor_name = session.get('user_name', 'Anonymous Donor')
        donor_email = session.get('user_email', 'anonymous@hemopulse.org')
        user_id = session.get('user_id', None)

        conn = get_db()
        cursor = conn.cursor()

        # Add to FIFO Inventory Vault
        cursor.execute("""
            INSERT INTO inventory (blood_group, component_type, units, donated_date, expiry_date, status)
            VALUES (?, ?, ?, ?, ?, 'ACTIVE')
        """, (blood_group, component_type, units, donation_date, expiry_date))

        # Log in Immutable Transaction Ledger
        cursor.execute("""
            INSERT INTO transactions (txn_type, person_name, blood_group, component_type, units, timestamp)
            VALUES ('IN', ?, ?, ?, ?, ?)
        """, (donor_name, blood_group, component_type, units, timestamp_str))

        # Log User Donation Record
        cursor.execute("""
            INSERT INTO donations (user_id, user_name, user_email, blood_group, component_type, units, donation_date, expiry_date, medical_condition, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'APPROVED')
        """, (user_id, donor_name, donor_email, blood_group, component_type, units, donation_date, expiry_date, medical_condition))

        conn.commit()
        conn.close()

        flash(f"Successfully vaulted +{units} Unit(s) of {blood_group} ({component_type}). Thank you for saving lives!", "success")
        return redirect(url_for('vault'))

    return render_template('donate.html')


# --- 3. EMERGENCY FIFO BLOOD REQUEST ---
@app.route('/request_blood', methods=['GET', 'POST'])
def request_blood():
    update_expired_inventory()
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        patient_name = request.form.get('patient_name')
        blood_group = request.form.get('blood_group')
        component_type = request.form.get('component_type')
        units_needed = int(request.form.get('units_needed', 1))
        hospital_id = request.form.get('hospital_id')

        # FIFO Query: Fetch Active Batches Nearest to Expiry First
        cursor.execute("""
            SELECT id, units, expiry_date FROM inventory
            WHERE blood_group = ? AND component_type = ? AND status = 'ACTIVE'
            ORDER BY date(expiry_date) ASC, id ASC
        """, (blood_group, component_type))

        available_batches = cursor.fetchall()
        total_available = sum(batch['units'] for batch in available_batches)

        if total_available < units_needed:
            conn.close()
            flash(f"Emergency Shortage: Only {total_available} Unit(s) available for {blood_group} ({component_type}). Requested: {units_needed}.", "danger")
            return redirect(url_for('request_blood'))

        # Execute Strict FIFO Algorithmic Deduction
        remaining_to_debit = units_needed
        for batch in available_batches:
            batch_id = batch['id']
            batch_units = batch['units']

            if batch_units <= remaining_to_debit:
                cursor.execute("UPDATE inventory SET units = 0, status = 'DISPATCHED' WHERE id = ?", (batch_id,))
                remaining_to_debit -= batch_units
            else:
                new_units = batch_units - remaining_to_debit
                cursor.execute("UPDATE inventory SET units = ? WHERE id = ?", (new_units, batch_id))
                remaining_to_debit = 0

            if remaining_to_debit == 0:
                break

        # Log Dispatch in Ledger
        timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            INSERT INTO transactions (txn_type, person_name, blood_group, component_type, units, hospital_id, timestamp)
            VALUES ('OUT', ?, ?, ?, ?, ?, ?)
        """, (patient_name, blood_group, component_type, units_needed, hospital_id, timestamp_str))

        conn.commit()
        conn.close()

        flash(f"FIFO Emergency Clearance: -{units_needed} Unit(s) of {blood_group} ({component_type}) successfully dispatched to Hospital Node.", "success")
        return redirect(url_for('transactions'))

    # Load hospital list for request form (Ordered Alphabetically)
    cursor.execute("SELECT id, hospital_name, district FROM hospitals ORDER BY hospital_name ASC")
    hospitals = cursor.fetchall()
    conn.close()

    return render_template('request_blood.html', hospitals=hospitals)


# --- 4. ACTIVE INVENTORY VAULT ---
@app.route('/vault')
def vault():
    update_expired_inventory()
    conn = get_db()
    cursor = conn.cursor()

    # Summary by blood group
    summary = {}
    for bg in ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-']:
        cursor.execute("SELECT SUM(units) FROM inventory WHERE blood_group = ? AND status = 'ACTIVE'", (bg,))
        res = cursor.fetchone()[0]
        summary[bg] = res if res else 0

    # Live FIFO Batches list
    cursor.execute("""
        SELECT id, blood_group, component_type, units, expiry_date
        FROM inventory
        WHERE status = 'ACTIVE' AND units > 0
        ORDER BY date(expiry_date) ASC
    """)
    rows = cursor.fetchall()

    today = datetime.now().date()
    batches = []
    for r in rows:
        exp_date = datetime.strptime(r['expiry_date'], '%Y-%m-%d').date()
        days_left = (exp_date - today).days
        batches.append({
            'batch_id': r['id'],
            'blood_group': r['blood_group'],
            'component_type': r['component_type'],
            'units': r['units'],
            'expiry_date': r['expiry_date'],
            'days_remaining': days_left
        })

    conn.close()
    return render_template('vault.html', summary=summary, batches=batches)


# --- 5. EXPIRED STOCK (QUARANTINE VAULT) ---
@app.route('/expired_vault')
def expired_vault():
    update_expired_inventory()
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, blood_group, component_type, units, donated_date, expiry_date
        FROM inventory
        WHERE status = 'EXPIRED'
        ORDER BY date(expiry_date) DESC
    """)
    items = cursor.fetchall()

    cursor.execute("SELECT SUM(units) FROM inventory WHERE status = 'EXPIRED'")
    res = cursor.fetchone()[0]
    total_expired = res if res else 0

    conn.close()
    return render_template('expired_vault.html', items=items, total_expired=total_expired)


# --- 6. TRANSACTION AUDIT LEDGER ---
@app.route('/transactions')
def transactions():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM transactions ORDER BY id DESC")
    raw_txns = cursor.fetchall()

    txns = []
    total_in = 0
    total_out = 0

    for t in raw_txns:
        if t['txn_type'] == 'IN':
            total_in += t['units']
        else:
            total_out += t['units']

        txns.append({
            'id': t['id'],
            'txn_type': t['txn_type'],
            'person_name': t['person_name'],
            'blood_group': t['blood_group'],
            'component_type': t['component_type'],
            'units': t['units'],
            'formatted_timestamp': t['timestamp']
        })

    conn.close()
    return render_template('transactions.html', transactions=txns, total_in=total_in, total_out=total_out)


# --- 7. USER AUTHENTICATION & DASHBOARD ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(email) = ? AND password = ?", (email, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password credentials. Please try again.", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        blood_group = request.form.get('blood_group', 'O+')
        password = request.form.get('password', '').strip()

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (name, email, password, blood_group)
                VALUES (?, ?, ?, ?)
            """, (name, email, password, blood_group))
            conn.commit()

            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            user_id = cursor.fetchone()[0]

            session['user_id'] = user_id
            session['user_name'] = name
            session['user_email'] = email
            conn.close()

            flash("Account registered successfully! Welcome to the HemoPulse Network.", "success")
            return redirect(url_for('dashboard'))
        except sqlite3.IntegrityError:
            conn.close()
            flash("An account with this email address already exists. Please login.", "danger")
            return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("You have been safely logged out.", "info")
    return redirect(url_for('index'))


@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    user_id = session.get('user_id')
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        age = request.form.get('age')
        gender = request.form.get('gender')
        blood_group = request.form.get('blood_group')

        cursor.execute("""
            UPDATE users 
            SET name = ?, age = ?, gender = ?, blood_group = ? 
            WHERE id = ?
        """, (name, age, gender, blood_group, user_id))
        conn.commit()

        session['user_name'] = name
        flash("Profile records updated successfully.", "success")

    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()

    cursor.execute("""
        SELECT * FROM donations 
        WHERE user_id = ? OR LOWER(user_email) = ?
        ORDER BY id DESC
    """, (user_id, session.get('user_email', '').lower()))
    user_donations = cursor.fetchall()

    conn.close()
    return render_template('dashboard.html', user=user, user_donations=user_donations)


# --- 8. OFFICIAL APPRECIATION CERTIFICATE (HTML/PRINT VIEW) ---
@app.route('/certificate/<int:donation_id>')
def certificate(donation_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM donations WHERE id = ?", (donation_id,))
    donation = cursor.fetchone()
    conn.close()

    if not donation:
        flash("Certificate record not found.", "danger")
        return redirect(url_for('dashboard'))

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>HemoPulse Lifesaver Certificate #HP-TX-{donation['id']}</title>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=Cinzel:wght@700&display=swap" rel="stylesheet">
        <style>
            body {{
                background: #080c14;
                color: #f1f5f9;
                font-family: 'Plus Jakarta Sans', sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                margin: 0;
            }}
            .certificate-card {{
                background: #0e1422;
                border: 2px solid rgba(245, 158, 11, 0.4);
                border-radius: 20px;
                padding: 50px 60px;
                max-width: 750px;
                text-align: center;
                box-shadow: 0 10px 40px rgba(0,0,0,0.8);
                position: relative;
            }}
            .cert-title {{
                font-family: 'Cinzel', serif;
                color: #fbbf24;
                font-size: 2.2rem;
                margin-bottom: 5px;
                letter-spacing: 2px;
            }}
            .cert-subtitle {{
                font-size: 0.85rem;
                color: #94a3b8;
                text-transform: uppercase;
                letter-spacing: 1.5px;
                margin-bottom: 30px;
            }}
            .donor-name {{
                font-size: 1.8rem;
                font-weight: 800;
                color: #ffffff;
                border-bottom: 2px solid rgba(225, 29, 72, 0.5);
                display: inline-block;
                padding-bottom: 5px;
                margin: 20px 0;
            }}
            .cert-desc {{
                font-size: 1rem;
                line-height: 1.8;
                color: #cbd5e1;
                margin-bottom: 30px;
            }}
            .details-box {{
                display: flex;
                justify-content: space-around;
                background: rgba(19, 27, 46, 0.8);
                border: 1px solid rgba(255,255,255,0.08);
                padding: 15px;
                border-radius: 10px;
                margin-bottom: 30px;
            }}
            .details-item span {{
                display: block;
                font-size: 0.75rem;
                color: #64748b;
                text-transform: uppercase;
            }}
            .details-item strong {{
                color: #38bdf8;
                font-size: 1.1rem;
            }}
            .print-btn {{
                background: linear-gradient(135deg, #e11d48, #be123c);
                border: none;
                color: #fff;
                font-weight: 700;
                padding: 12px 30px;
                border-radius: 8px;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
            }}
            @media print {{
                .print-btn {{ display: none; }}
                body {{ background: #fff; color: #000; }}
                .certificate-card {{ border: 2px solid #000; box-shadow: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="certificate-card">
            <div class="cert-title">Certificate of Honor</div>
            <div class="cert-subtitle">HemoPulse Emergency Blood Reserve Ecosystem</div>
            
            <p>This credential is proudly presented to</p>
            <div class="donor-name">{donation['user_name']}</div>
            
            <div class="cert-desc">
                In sincere appreciation of your voluntary life-saving blood donation. Your contribution has been verified and registered into the regional emergency vault.
            </div>

            <div class="details-box">
                <div class="details-item">
                    <span>Blood Group</span>
                    <strong style="color:#f43f5e;">{donation['blood_group']}</strong>
                </div>
                <div class="details-item">
                    <span>Component</span>
                    <strong>{donation['component_type']}</strong>
                </div>
                <div class="details-item">
                    <span>Quantity</span>
                    <strong>{donation['units']} Unit(s)</strong>
                </div>
                <div class="details-item">
                    <span>Donation Date</span>
                    <strong>{donation['donation_date']}</strong>
                </div>
            </div>

            <button class="print-btn" onclick="window.print()">Print / Save PDF</button>
        </div>
    </body>
    </html>
    """


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == '__main__':
    init_db()
    update_expired_inventory()
    print("==========================================================")
    print(" HemoPulse Emergency Vault Server Live: http://127.0.0.1:5000")
    print("==========================================================")
    app.run(debug=True, port=5000)