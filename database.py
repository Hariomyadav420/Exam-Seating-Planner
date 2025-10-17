# database.py
import sqlite3
import pandas as pd
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "exam_seating.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            roll_no TEXT PRIMARY KEY,
            name TEXT,
            course TEXT,
            semester TEXT,
            email TEXT,
            subject_code TEXT
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            room_no TEXT PRIMARY KEY,
            building TEXT,
            rows INTEGER,
            columns INTEGER,
            capacity INTEGER
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS seating_allocations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no TEXT,
            room_no TEXT,
            row_num INTEGER,
            col_num INTEGER,
            seat_number TEXT,
            allocation_method TEXT,
            FOREIGN KEY (roll_no) REFERENCES students(roll_no),
            FOREIGN KEY (room_no) REFERENCES rooms(room_no)
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_type TEXT,
            description TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    conn.commit()
    conn.close()

# --------------------- Users ---------------------
def insert_user(username, password_hash, is_admin=1):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO users (username, password_hash, is_admin)
            VALUES (?, ?, ?)
        ''', (username, password_hash, is_admin))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def get_user_by_username(username):
    conn = get_connection()
    cursor = conn.cursor()
    user = cursor.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return user

# --------------------- Students/Rooms/Allocations ---------------------
def insert_students(df):
    conn = get_connection()
    cursor = conn.cursor()
    for _, row in df.iterrows():
        try:
            cursor.execute('''
                INSERT INTO students (roll_no, name, course, semester, email, subject_code)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (str(row['Roll No']).strip(), str(row['Name']).strip(), str(row['Course/Program']).strip(),
                  str(row['Semester']).strip(), str(row['Email']).strip(), str(row['Subject Code']).strip()))
        except Exception:
            # skip malformed row or duplicates
            pass
    conn.commit()
    conn.close()

def insert_rooms(df):
    conn = get_connection()
    cursor = conn.cursor()
    for _, row in df.iterrows():
        try:
            cursor.execute('''
                INSERT INTO rooms (room_no, building, rows, columns, capacity)
                VALUES (?, ?, ?, ?, ?)
            ''', (str(row['Room No']).strip(), str(row['Building']).strip(),
                  int(row['Rows']), int(row['Columns']), int(row['Capacity'])))
        except Exception:
            pass
    conn.commit()
    conn.close()

def clear_students():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM students')
    conn.commit()
    conn.close()

def clear_rooms():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM rooms')
    conn.commit()
    conn.close()

def clear_allocations():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM seating_allocations')
    conn.commit()
    conn.close()

def insert_allocation(roll_no, room_no, row_num, col_num, seat_number, method):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO seating_allocations (roll_no, room_no, row_num, col_num, seat_number, allocation_method)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (roll_no, room_no, row_num, col_num, seat_number, method))
    conn.commit()
    conn.close()

# --------------------- Queries ---------------------
def get_all_students():
    conn = get_connection()
    cursor = conn.cursor()
    rows = cursor.execute('SELECT * FROM students ORDER BY roll_no').fetchall()
    conn.close()
    return rows

def get_all_rooms():
    conn = get_connection()
    cursor = conn.cursor()
    rows = cursor.execute('SELECT * FROM rooms ORDER BY room_no').fetchall()
    conn.close()
    return rows

def get_allocations_by_room(room_no):
    """Get all allocations for a specific room with student details including email."""
    conn = get_connection()
    cursor = conn.cursor()
    rows = cursor.execute('''
        SELECT sa.*, s.name, s.course, s.semester, s.email, s.subject_code
        FROM seating_allocations sa
        LEFT JOIN students s ON sa.roll_no = s.roll_no
        WHERE sa.room_no = ?
        ORDER BY sa.row_num, sa.col_num
    ''', (room_no,)).fetchall()
    conn.close()
    return rows

def get_all_allocations():
    """Get all allocations with student and room details including email."""
    conn = get_connection()
    cursor = conn.cursor()
    rows = cursor.execute('''
        SELECT sa.*, s.name, s.course, s.semester, s.email, s.subject_code, r.building
        FROM seating_allocations sa
        LEFT JOIN students s ON sa.roll_no = s.roll_no
        LEFT JOIN rooms r ON sa.room_no = r.room_no
        ORDER BY sa.room_no, sa.row_num, sa.col_num
    ''').fetchall()
    conn.close()
    return rows

def get_allocation_by_roll(roll_no):
    """Get allocation for a specific student with all details including email."""
    conn = get_connection()
    cursor = conn.cursor()
    row = cursor.execute('''
        SELECT sa.*, s.name, s.course, s.semester, s.email, s.subject_code, r.building
        FROM seating_allocations sa
        LEFT JOIN students s ON sa.roll_no = s.roll_no
        LEFT JOIN rooms r ON sa.room_no = r.room_no
        WHERE sa.roll_no = ?
    ''', (roll_no,)).fetchone()
    conn.close()
    return row

# --------------------- Validation helpers ---------------------
def validate_students_file(df):
    required = {'Roll No', 'Name', 'Course/Program', 'Semester', 'Email', 'Subject Code'}
    if not required.issubset(set(df.columns)):
        missing = required - set(df.columns)
        return (False, f'Missing columns in students file: {", ".join(missing)}')
    # simple duplicate check
    if df['Roll No'].duplicated().any():
        return (False, 'Duplicate roll numbers found in the uploaded file.')
    return (True, 'Valid')

def validate_rooms_file(df):
    required = {'Room No', 'Building', 'Rows', 'Columns', 'Capacity'}
    if not required.issubset(set(df.columns)):
        missing = required - set(df.columns)
        return (False, f'Missing columns in rooms file: {", ".join(missing)}')
    if df['Room No'].duplicated().any():
        return (False, 'Duplicate room numbers found in the uploaded file.')
    return (True, 'Valid')

# --------------------- Capacity check ---------------------
def check_capacity():
    conn = get_connection()
    cursor = conn.cursor()
    total_students = cursor.execute('SELECT COUNT(*) FROM students').fetchone()[0]
    total_capacity = cursor.execute('SELECT SUM(capacity) FROM rooms').fetchone()[0] or 0
    conn.close()
    return (total_students, total_capacity, total_capacity >= total_students)

# --------------------- Activity log ---------------------
def log_activity(activity_type, description):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO activity_log (activity_type, description)
        VALUES (?, ?)
    ''', (activity_type, description))
    conn.commit()
    conn.close()

# --------------------- Swap seats ---------------------
def swap_seats(roll1, roll2, performed_by=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM seating_allocations WHERE roll_no = ?', (roll1,))
        r1 = cursor.fetchone()
        cursor.execute('SELECT * FROM seating_allocations WHERE roll_no = ?', (roll2,))
        r2 = cursor.fetchone()

        if not r1 and not r2:
            conn.close()
            return (False, f'Neither roll number {roll1} nor {roll2} have seat allocations.')
        if not r1:
            conn.close()
            return (False, f'Roll number {roll1} has no allocation to swap.')
        if not r2:
            conn.close()
            return (False, f'Roll number {roll2} has no allocation to swap.')

        r1_room, r1_row, r1_col, r1_seat = r1['room_no'], r1['row_num'], r1['col_num'], r1['seat_number']
        r2_room, r2_row, r2_col, r2_seat = r2['room_no'], r2['row_num'], r2['col_num'], r2['seat_number']

        cursor.execute('BEGIN')
        cursor.execute('''
            UPDATE seating_allocations
            SET room_no = ?, row_num = ?, col_num = ?, seat_number = ?
            WHERE roll_no = ?
        ''', (r2_room, r2_row, r2_col, r2_seat, roll1))
        cursor.execute('''
            UPDATE seating_allocations
            SET room_no = ?, row_num = ?, col_num = ?, seat_number = ?
            WHERE roll_no = ?
        ''', (r1_room, r1_row, r1_col, r1_seat, roll2))

        actor = performed_by or 'system'
        description = f"Seat swap by {actor}: {roll1} <-> {roll2} (rooms: {r1_room}<->{r2_room}; seats: {r1_seat}<->{r2_seat})"
        cursor.execute('INSERT INTO activity_log (activity_type, description) VALUES (?, ?)', ('seat_swap', description))

        conn.commit()
        conn.close()
        return (True, f'Successfully swapped seats between {roll1} and {roll2}.')
    except Exception as e:
        conn.rollback()
        conn.close()
        return (False, f'Error while swapping seats: {str(e)}')