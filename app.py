from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, session, flash
from datetime import datetime, timedelta
import os
import sqlite3
import io
from werkzeug.utils import secure_filename
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'dev-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['EXPORT_FOLDER'] = 'exports'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'csv', 'xlsx', 'xls'}

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['EXPORT_FOLDER'], exist_ok=True)

# --------------------------- Helper Functions ---------------------------

@app.template_filter('datetimeformat')
def format_datetime(value, format_str='%b %d, %Y %I:%M %p'):
    """Convert UTC timestamps to IST format for display."""
    if value is None:
        return ""
    if isinstance(value, str):
        try:
            if '.' in value:
                dt_utc = datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f')
            else:
                dt_utc = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return value
    else:
        dt_utc = value
    dt_ist = dt_utc + timedelta(hours=5, minutes=30)
    return dt_ist.strftime(format_str)


def allowed_file(filename):
    """Check if uploaded file is allowed (CSV/Excel)."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def get_db():
    """Return SQLite connection."""
    conn = sqlite3.connect('exam_seating.db')
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables if not exist."""
    conn = get_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        is_admin BOOLEAN DEFAULT 0
    )
    ''')

    # Default admin
    cursor.execute('SELECT COUNT(*) FROM users')
    if cursor.fetchone()[0] == 0:
        default_admin_password = generate_password_hash('adminpass')
        cursor.execute('INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)',
                       ('admin', default_admin_password, 1))
        print("✅ Default admin user 'admin' created (password: adminpass)")

    # Students
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        roll_no TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        course TEXT NOT NULL,
        semester TEXT NOT NULL,
        email TEXT NOT NULL,
        subject_code TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Rooms
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_no TEXT UNIQUE NOT NULL,
        building TEXT NOT NULL,
        rows INTEGER NOT NULL,
        columns INTEGER NOT NULL,
        capacity INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Seating allocations
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS seating_allocations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        roll_no TEXT NOT NULL,
        room_no TEXT NOT NULL,
        row_num INTEGER NOT NULL,
        col_num INTEGER NOT NULL,
        seat_number TEXT NOT NULL,
        allocation_method TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (roll_no) REFERENCES students (roll_no),
        FOREIGN KEY (room_no) REFERENCES rooms (room_no)
    )
    ''')

    # Activity log
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        activity_type TEXT NOT NULL,
        description TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    conn.commit()
    conn.close()

# --------------------------- Routes ---------------------------

@app.route('/')
def index():
    logged_in = session.get('logged_in', False)
    return render_template('index.html', logged_in=logged_in)


# ---------- Authentication ----------

@app.route('/register', methods=['GET', 'POST'])
def register():
    from database import insert_user
    if request.method == 'POST':
        username = request.form.get('email')
        name = request.form.get('name')
        phone = request.form.get('phone')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not username or not password or not confirm_password:
            flash("All fields are required.", 'danger')
            return render_template('registration.html')

        if password != confirm_password:
            flash("Passwords do not match.", 'danger')
            return render_template('registration.html')

        hashed_password = generate_password_hash(password)
        if insert_user(username, hashed_password):
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash("Username already exists.", 'danger')

    return render_template('registration.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    from database import get_user_by_username
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = get_user_by_username(username)
        if user and check_password_hash(user['password_hash'], password):
            session['logged_in'] = True
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            return redirect(url_for('admin'))
        else:
            flash("Invalid username or password.", "danger")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# ---------- Admin Dashboard ----------

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()

    student_count = cursor.execute('SELECT COUNT(*) FROM students').fetchone()[0]
    room_count = cursor.execute('SELECT COUNT(*) FROM rooms').fetchone()[0]
    allocation_count = cursor.execute('SELECT COUNT(*) FROM seating_allocations').fetchone()[0]
    recent_activities = cursor.execute('SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT 10').fetchall()

    conn.close()

    return render_template('admin.html',
                           student_count=student_count,
                           room_count=room_count,
                           allocation_count=allocation_count,
                           recent_activities=recent_activities)


# ---------- Seat Swap (Admin only) ----------

@app.route('/api/swap_seats', methods=['POST'])
def swap_seats_route():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Authentication required'}), 401

    if not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Admin privileges required'}), 403

    data = request.get_json() or {}
    roll1 = (data.get('roll1') or '').strip()
    roll2 = (data.get('roll2') or '').strip()

    if not roll1 or not roll2:
        return jsonify({'success': False, 'message': 'Both roll numbers are required'}), 400
    if roll1 == roll2:
        return jsonify({'success': False, 'message': 'Please provide two different roll numbers'}), 400

    from database import swap_seats
    performed_by = session.get('username', 'admin')
    success, message = swap_seats(roll1, roll2, performed_by)

    return jsonify({'success': success, 'message': message}), (200 if success else 400)


# ---------- Student, Invigilator Portals ----------

@app.route('/student')
def student_portal():
    return render_template('student.html')


@app.route('/invigilator')
def invigilator_panel():
    conn = get_db()
    cursor = conn.cursor()
    rooms = cursor.execute('SELECT * FROM rooms ORDER BY room_no').fetchall()
    conn.close()
    return render_template('invigilator.html', rooms=rooms)


# ---------- Student Portal API ----------
@app.route('/api/student/<roll_no>', methods=['GET'])
def get_student_allocation(roll_no):
    """Get seat allocation for a specific student by roll number."""
    from database import get_allocation_by_roll
    
    allocation = get_allocation_by_roll(roll_no)
    
    if not allocation:
        return jsonify({
            'success': False,
            'message': 'No seat allocation found for this roll number. Please contact the exam office.'
        }), 404
    
    return jsonify({
        'success': True,
        'data': {
            'roll_no': allocation['roll_no'],
            'name': allocation['name'],
            'course': allocation['course'],
            'semester': allocation['semester'],
            'subject_code': allocation['subject_code'],
            'email': allocation['email'],
            'room_no': allocation['room_no'],
            'building': allocation['building'],
            'seat_number': allocation['seat_number'],
            'row': allocation['row_num'],
            'column': allocation['col_num']
        }
    })


# ---------- Invigilator API Routes ----------
@app.route('/api/room/<room_no>/allocations', methods=['GET'])
def get_room_allocations(room_no):
    """Get all allocations for a specific room with seat mapping."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get room details
    room = cursor.execute('SELECT * FROM rooms WHERE room_no = ?', (room_no,)).fetchone()
    if not room:
        conn.close()
        return jsonify({'success': False, 'message': 'Room not found'}), 404
    
    # Get all allocations for this room
    allocations_raw = cursor.execute('''
        SELECT sa.*, s.name, s.course, s.semester, s.email, s.subject_code
        FROM seating_allocations sa
        JOIN students s ON sa.roll_no = s.roll_no
        WHERE sa.room_no = ?
        ORDER BY sa.row_num, sa.col_num
    ''', (room_no,)).fetchall()
    
    conn.close()
    
    # Create a dictionary mapping row-col to student data
    allocations = {}
    for alloc in allocations_raw:
        key = f"{alloc['row_num']}-{alloc['col_num']}"
        allocations[key] = {
            'roll_no': alloc['roll_no'],
            'name': alloc['name'],
            'course': alloc['course'],
            'semester': alloc['semester'],
            'email': alloc['email'],
            'subject_code': alloc['subject_code'],
            'seat_number': alloc['seat_number'],
            'row_num': alloc['row_num'],
            'col_num': alloc['col_num']
        }
    
    return jsonify({
        'success': True,
        'room': {
            'room_no': room['room_no'],
            'building': room['building'],
            'rows': room['rows'],
            'columns': room['columns'],
            'capacity': room['capacity']
        },
        'allocations': allocations
    })


@app.route('/api/room/<room_no>/export', methods=['GET'])
def export_room_list(room_no):
    """Export room-specific seating list to Excel."""
    from exporter import export_room_wise_excel
    try:
        filepath = export_room_wise_excel(room_no)
        if not filepath:
            return jsonify({'success': False, 'message': f'No allocations found for room {room_no}'}), 404
        return send_file(filepath, as_attachment=True, download_name=f'room_{room_no}_list.xlsx')
    except Exception as e:
        return jsonify({'success': False, 'message': f'Export error: {str(e)}'}), 500


# ---------- Upload Students ----------
@app.route('/api/upload_students', methods=['POST'])
def upload_students():
    from database import validate_students_file, insert_students, log_activity, clear_students
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file provided'}), 400

    file = request.files['file']
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'Invalid file type'}), 400

    try:
        df = pd.read_csv(file) if file.filename.endswith('.csv') else pd.read_excel(file)
        valid, msg = validate_students_file(df)
        if not valid:
            return jsonify({'success': False, 'message': msg}), 400
        clear_students()
        insert_students(df)
        log_activity('upload', f'Uploaded {len(df)} students')
        return jsonify({'success': True, 'message': f'Uploaded {len(df)} students'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ---------- Upload Rooms ----------
@app.route('/api/upload_rooms', methods=['POST'])
def upload_rooms():
    from database import validate_rooms_file, insert_rooms, log_activity, clear_rooms
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file provided'}), 400

    file = request.files['file']
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'Invalid file type'}), 400

    try:
        df = pd.read_csv(file) if file.filename.endswith('.csv') else pd.read_excel(file)
        valid, msg = validate_rooms_file(df)
        if not valid:
            return jsonify({'success': False, 'message': msg}), 400
        clear_rooms()
        insert_rooms(df)
        log_activity('upload', f'Uploaded {len(df)} rooms')
        return jsonify({'success': True, 'message': f'Uploaded {len(df)} rooms'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ---------- Allocation ----------
@app.route('/api/allocate', methods=['POST'])
def allocate_seats():
    from database import check_capacity
    from allocator import allocate_rollwise, allocate_random, allocate_anti_cheating
    data = request.get_json() or {}
    method = data.get('method', 'anti-cheating')

    student_count, capacity, sufficient = check_capacity()
    if not sufficient:
        return jsonify({'success': False, 'message': f'Insufficient capacity: {student_count} students, {capacity} seats'}), 400

    try:
        if method == 'rollwise':
            success, message = allocate_rollwise()
        elif method == 'random':
            success, message = allocate_random()
        else:
            success, message = allocate_anti_cheating()
        return jsonify({'success': success, 'message': message}), (200 if success else 400)
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


@app.route('/api/allocate_anti_cheating', methods=['POST'])
def allocate_anti_cheating_route():
    """Dedicated endpoint for anti-cheating zig-zag allocation."""
    from database import check_capacity
    from allocator import allocate_anti_cheating
    
    student_count, capacity, sufficient = check_capacity()
    if not sufficient:
        return jsonify({
            'success': False, 
            'message': f'Insufficient capacity: {student_count} students, {capacity} seats'
        }), 400

    try:
        success, message = allocate_anti_cheating()
        return jsonify({
            'success': success,
            'message': message
        }), (200 if success else 400)
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Allocation error: {str(e)}'
        }), 500


# ---------- Admit Cards ----------
@app.route('/api/generate_admit_cards', methods=['POST'])
def generate_admit_cards():
    from exporter import generate_all_admit_cards
    try:
        success, message = generate_all_admit_cards()
        return jsonify({'success': success, 'message': message}), (200 if success else 400)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/download_admit_card/<roll_no>', methods=['GET'])
def download_admit_card(roll_no):
    from exporter import generate_admit_card_pdf
    filepath = f'exports/admit_cards/{roll_no}_admit_card.pdf'
    os.makedirs('exports/admit_cards', exist_ok=True)
    if not os.path.exists(filepath):
        ok, _ = generate_admit_card_pdf(roll_no, filepath)
        if not ok:
            return jsonify({'success': False, 'message': 'Admit card not found'}), 404
    return send_file(filepath, as_attachment=True, download_name=f'{roll_no}_admit_card.pdf')


# ---------- Export Excel ----------
@app.route('/api/export_excel', methods=['GET'])
def export_excel():
    """Export complete seating plan to Excel."""
    from exporter import export_seating_plan_excel
    try:
        filepath = export_seating_plan_excel()
        if not filepath:
            return jsonify({'success': False, 'message': 'No allocations to export'}), 404
        return send_file(filepath, as_attachment=True, download_name='seating_plan.xlsx')
    except Exception as e:
        return jsonify({'success': False, 'message': f'Export error: {str(e)}'}), 500


@app.route('/api/export_room/<room_no>', methods=['GET'])
def export_room(room_no):
    """Export room-wise seating plan to Excel."""
    from exporter import export_room_wise_excel
    try:
        filepath = export_room_wise_excel(room_no)
        if not filepath:
            return jsonify({'success': False, 'message': f'No allocations found for room {room_no}'}), 404
        return send_file(filepath, as_attachment=True, download_name=f'room_{room_no}_list.xlsx')
    except Exception as e:
        return jsonify({'success': False, 'message': f'Export error: {str(e)}'}), 500


# ---------- Statistics ----------
@app.route('/api/stats', methods=['GET'])
def get_stats():
    conn = get_db()
    cursor = conn.cursor()

    student_count = cursor.execute('SELECT COUNT(*) FROM students').fetchone()[0]
    room_count = cursor.execute('SELECT COUNT(*) FROM rooms').fetchone()[0]
    allocation_count = cursor.execute('SELECT COUNT(*) FROM seating_allocations').fetchone()[0]
    total_capacity = cursor.execute('SELECT SUM(capacity) FROM rooms').fetchone()[0] or 0

    rooms = cursor.execute('SELECT * FROM rooms').fetchall()
    room_utilization = []
    for room in rooms:
        allocated = cursor.execute('SELECT COUNT(*) FROM seating_allocations WHERE room_no=?', (room['room_no'],)).fetchone()[0]
        room_utilization.append({
            'room_no': room['room_no'],
            'capacity': room['capacity'],
            'allocated': allocated,
            'percentage': round((allocated / room['capacity'] * 100), 1) if room['capacity'] > 0 else 0
        })

    conn.close()
    return jsonify({'success': True, 'stats': {
        'students': student_count,
        'rooms': room_count,
        'allocations': allocation_count,
        'total_capacity': total_capacity,
        'room_utilization': room_utilization
    }})

# --------------------------- Run App ---------------------------

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)