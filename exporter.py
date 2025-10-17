import os
import io
import qrcode
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import pandas as pd
from database import get_all_allocations, get_allocation_by_roll
from datetime import datetime

def generate_qr_code(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    return img_buffer

def generate_admit_card_pdf(roll_no, output_path):
    allocation = get_allocation_by_roll(roll_no)
    if not allocation:
        return False, f"No allocation found for roll no {roll_no}"

    # Convert to dict for safe .get() usage
    allocation = dict(allocation)

    def safe(key):
        return allocation.get(key, '')

    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width / 2, height - 1 * inch, "EXAM ADMIT CARD")

    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, height - 1.3 * inch, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    y_position = height - 2 * inch
    c.setFont("Helvetica-Bold", 12)

    details = [
        ("Roll Number:", safe('roll_no')),
        ("Name:", safe('name')),
        ("Course/Program:", safe('course')),
        ("Semester:", safe('semester')),
        ("Subject Code:", safe('subject_code')),
        ("", ""),
        ("Exam Room:", f"{safe('room_no')} - {safe('building')}"),
        ("Seat Number:", safe('seat_number')),
        ("Row:", str(safe('row_num'))),
        ("Column:", str(safe('col_num')))
    ]

    for label, value in details:
        if label:
            c.setFont("Helvetica-Bold", 12)
            c.drawString(1.5 * inch, y_position, label)
            c.setFont("Helvetica", 12)
            c.drawString(3.5 * inch, y_position, str(value))
        y_position -= 0.4 * inch

    qr_data = f"Roll: {safe('roll_no')} | Room: {safe('room_no')} | Seat: {safe('seat_number')}"
    qr_buffer = generate_qr_code(qr_data)
    qr_image = ImageReader(qr_buffer)

    qr_x = width / 2 - 1 * inch
    qr_y = 2 * inch
    c.drawImage(qr_image, qr_x, qr_y, width=2 * inch, height=2 * inch, mask='auto')

    c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(width / 2, 1.5 * inch, "Scan QR code for verification")

    c.rect(0.5 * inch, 0.5 * inch, width - 1 * inch, height - 1 * inch, stroke=1, fill=0)
    y_inst_start = 1.5 * inch

    c.setFont("Helvetica-Bold", 10)
    c.drawString(1 * inch, y_inst_start, "Important Instructions:")

    c.setFont("Helvetica", 9)
    instructions = [
        "1. Bring this admit card to the examination hall",
        "2. Report 30 minutes before exam start time",
        "3. Carry a valid ID proof",
        "4. Mobile phones and electronic devices are not allowed"
    ]

    y_inst = y_inst_start - 0.25 * inch 
    for instruction in instructions:
        c.drawString(1 * inch, y_inst, instruction)
        y_inst -= 0.15 * inch

    c.save()
    return True, "Admit card generated"

def generate_all_admit_cards():
    allocations = get_all_allocations()
    if not allocations:
        return False, "No allocations found"
    output_dir = 'exports/admit_cards'
    os.makedirs(output_dir, exist_ok=True)
    errors = []
    for allocation in allocations:
        allocation = dict(allocation)
        filename = f"{allocation.get('roll_no','unknown')}_admit_card.pdf"
        filepath = os.path.join(output_dir, filename)
        ok, msg = generate_admit_card_pdf(allocation.get('roll_no'), filepath)
        if not ok:
            errors.append(msg)
    if errors:
        return False, "Some admit cards failed:\n" + "\n".join(errors)
    return True, f"Generated {len(allocations)} admit cards in {output_dir}"

def export_seating_plan_excel():
    allocations = get_all_allocations()
    if not allocations:
        return None
    data = []
    for allocation in allocations:
        allocation = dict(allocation)
        data.append({
            'Roll No': allocation.get('roll_no', ''),
            'Name': allocation.get('name', ''),
            'Course': allocation.get('course', ''),
            'Semester': allocation.get('semester', ''),
            'Subject Code': allocation.get('subject_code', ''),
            'Email': allocation.get('email', ''),
            'Room No': allocation.get('room_no', ''),
            'Building': allocation.get('building', ''),
            'Seat Number': allocation.get('seat_number', ''),
            'Row': allocation.get('row_num', ''),
            'Column': allocation.get('col_num', ''),
            'Allocation Method': allocation.get('allocation_method', '')
        })
    df = pd.DataFrame(data)
    output_path = 'exports/seating_plan.xlsx'
    os.makedirs('exports', exist_ok=True)
    df.to_excel(output_path, index=False, sheet_name='Seating Plan')
    return output_path

def export_room_wise_excel(room_no):
    from database import get_allocations_by_room
    allocations = get_allocations_by_room(room_no)
    if not allocations:
        return None
    data = []
    for allocation in allocations:
        allocation = dict(allocation)
        data.append({
            'Seat Number': allocation.get('seat_number', ''),
            'Row': allocation.get('row_num', ''),
            'Column': allocation.get('col_num', ''),
            'Roll No': allocation.get('roll_no', ''),
            'Name': allocation.get('name', ''),
            'Course': allocation.get('course', ''),
            'Subject Code': allocation.get('subject_code', ''),
            'Email': allocation.get('email', '')
        })
    df = pd.DataFrame(data)
    output_path = f'exports/room_{room_no}_list.xlsx'
    os.makedirs('exports', exist_ok=True)
    df.to_excel(output_path, index=False, sheet_name=f'Room {room_no}')
    return output_path