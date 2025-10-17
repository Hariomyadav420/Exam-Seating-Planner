import random
from collections import defaultdict
from database import get_all_students, get_all_rooms, insert_allocation, clear_allocations, log_activity


def allocate_rollwise():
    """
    Allocates students roll-number wise sequentially across available rooms and seats.
    """
    clear_allocations()

    students = get_all_students()
    rooms = get_all_rooms()

    if not students or not rooms:
        return False, "No students or rooms available"

    students_sorted = sorted(students, key=lambda x: x['roll_no'])

    room_seats = []
    for room in rooms:
        for row in range(1, room['rows'] + 1):
            for col in range(1, room['columns'] + 1):
                room_seats.append({
                    'room_no': room['room_no'],
                    'row': row,
                    'col': col,
                    'seat_number': f"{room['room_no']}-R{row}C{col}"
                })

    allocated = 0
    for i, student in enumerate(students_sorted):
        if i < len(room_seats):
            seat = room_seats[i]
            insert_allocation(
                student['roll_no'],
                seat['room_no'],
                seat['row'],
                seat['col'],
                seat['seat_number'],
                'rollwise'
            )
            allocated += 1

    log_activity('allocation', f'Roll-wise allocation completed: {allocated} students allocated')
    return True, f"Successfully allocated {allocated} students rollwise."


def allocate_random():
    """
    Randomly allocates students to available seats across rooms.
    """
    clear_allocations()

    students = get_all_students()
    rooms = get_all_rooms()

    if not students or not rooms:
        return False, "No students or rooms available"

    students_list = list(students)
    random.shuffle(students_list)

    room_seats = []
    for room in rooms:
        for row in range(1, room['rows'] + 1):
            for col in range(1, room['columns'] + 1):
                room_seats.append({
                    'room_no': room['room_no'],
                    'row': row,
                    'col': col,
                    'seat_number': f"{room['room_no']}-R{row}C{col}"
                })

    allocated = 0
    for i, student in enumerate(students_list):
        if i < len(room_seats):
            seat = room_seats[i]
            insert_allocation(
                student['roll_no'],
                seat['room_no'],
                seat['row'],
                seat['col'],
                seat['seat_number'],
                'random'
            )
            allocated += 1

    log_activity('allocation', f'Random allocation completed: {allocated} students allocated')
    return True, f"Successfully allocated {allocated} students randomly."


def allocate_anti_cheating():
    """
    Anti-Cheating Zig-Zag Allocation:
    Mixes students from two different courses in a zig-zag pattern (A-B-A-B),
    ensuring students from the same course do not sit next to each other.
    Only accessible to the Admin via the panel.
    """
    clear_allocations()

    students = get_all_students()
    rooms = get_all_rooms()

    if not students or not rooms:
        return False, "No students or rooms available"

    # Group students by subject_code
    subject_groups = defaultdict(list)
    for student in students:
        subject_groups[student['subject_code']].append(student)

    if len(subject_groups) < 2:
        return False, "Need at least two different courses for anti-cheating allocation"

    # Use first two subject groups for zig-zag mixing
    subjects = list(subject_groups.keys())[:2]
    course_a, course_b = subjects[0], subjects[1]

    # Shuffle each course list to ensure randomness
    random.shuffle(subject_groups[course_a])
    random.shuffle(subject_groups[course_b])

    a_index, b_index = 0, 0
    allocated = 0

    # --- Zig-Zag Allocation Logic ---
    for room in rooms:
        total_rows = room['rows']
        total_cols = room['columns']

        for r in range(total_rows):
            # Even rows: A-B-A-B | Odd rows: B-A-B-A
            zigzag_order = [course_a, course_b] if r % 2 == 0 else [course_b, course_a]

            for c in range(total_cols):
                current_course = zigzag_order[c % 2]
                if current_course == course_a and a_index < len(subject_groups[course_a]):
                    student = subject_groups[course_a][a_index]
                    a_index += 1
                elif current_course == course_b and b_index < len(subject_groups[course_b]):
                    student = subject_groups[course_b][b_index]
                    b_index += 1
                else:
                    # Fill leftover seats with whichever course still has students
                    if a_index < len(subject_groups[course_a]):
                        student = subject_groups[course_a][a_index]
                        a_index += 1
                    elif b_index < len(subject_groups[course_b]):
                        student = subject_groups[course_b][b_index]
                        b_index += 1
                    else:
                        continue

                seat_number = f"{room['room_no']}-R{r+1}C{c+1}"
                insert_allocation(
                    student['roll_no'],
                    room['room_no'],
                    r + 1,
                    c + 1,
                    seat_number,
                    'anti-cheating'
                )
                allocated += 1

    log_activity('allocation', f'Anti-Cheating (Zig-Zag) allocation completed: {allocated} students allocated')
    return True, f"Successfully allocated {allocated} students in Anti-Cheating Zig-Zag mode."