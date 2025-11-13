from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import date
import calendar as cal

import pandas as pd
import streamlit as st

DB_PATH = Path("students.db")

DEFAULT_ADMIN = {"username": "admin", "password": "admin123", "full_name": "Administrator"}

DEFAULT_STUDENTS = [
    {
        "username": "sara", "password": "sara2024", "full_name": "Sara Hernandez",
        "email": "sara.hernandez@example.com", "program": "Computer Science",
        "phone": "(555) 010-1111", "notes": "Robotics club president.",
    },
    {
        "username": "dylan", "password": "dylan2024", "full_name": "Dylan Chen",
        "email": "dylan.chen@example.com", "program": "Mechanical Engineering",
        "phone": "(555) 010-2222", "notes": "Co-op placement at Horizon Industries.",
    },
    {
        "username": "lina", "password": "lina2024", "full_name": "Lina Patel",
        "email": "lina.patel@example.com", "program": "Business Administration",
        "phone": "(555) 010-3333", "notes": "Dean's list for two consecutive years.",
    },
]

# Constants for attendance
ATTENDANCE_COLORS = {
    "present": {"bg": "#22c55e", "light_bg": "#d1fae5", "label": "P", "icon": "✓"},
    "absent": {"bg": "#ef4444", "light_bg": "#fee2e2", "label": "A", "icon": "✗"},
    "unmarked": {"bg": "#e5e7eb", "light_bg": "#f3f4f6", "label": "", "icon": ""}
}


@st.cache_resource(show_spinner=False)
def get_connection():
    import sqlite3
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def safe_db_execute(query: str, params: tuple = (), commit: bool = True) -> Optional[str]:
    """Execute a database operation safely, returning error message if any."""
    try:
        conn = get_connection()
        if commit:
            with conn:
                conn.execute(query, params)
        else:
            conn.execute(query, params)
        return None
    except Exception as exc:
        return str(exc)


def init_db() -> None:
    conn = get_connection()
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                full_name TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                program TEXT NOT NULL,
                phone TEXT,
                notes TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS student_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_username TEXT NOT NULL,
                title TEXT NOT NULL,
                file_name TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                data BLOB NOT NULL,
                uploaded_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (student_username) REFERENCES students(username) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_username TEXT NOT NULL,
                attendance_date TEXT NOT NULL,
                status TEXT NOT NULL,
                marked_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (student_username) REFERENCES students(username) ON DELETE CASCADE,
                UNIQUE(student_username, attendance_date)
            )
            """
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO admins (username, password, full_name)
            VALUES (:username, :password, :full_name)
            """,
            DEFAULT_ADMIN,
        )

        existing_usernames = {
            row["username"]
            for row in conn.execute("SELECT username FROM students")
        }
        for student in DEFAULT_STUDENTS:
            if student["username"] not in existing_usernames:
                conn.execute(
                    """
                    INSERT INTO students (username, password, full_name, email, program, phone, notes)
                    VALUES (:username, :password, :full_name, :email, :program, :phone, :notes)
                    """,
                    student,
                )


def fetch_students() -> List[Dict[str, str]]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT username, full_name, email, program, phone, notes
        FROM students
        ORDER BY username
        """
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_student(username: str) -> Optional[Dict[str, str]]:
    conn = get_connection()
    row = conn.execute(
        """
        SELECT username, password, full_name, email, program, phone, notes
        FROM students
        WHERE username = ?
        """,
        (username,),
    ).fetchone()
    return dict(row) if row else None


def add_student(payload: Dict[str, str]) -> Optional[str]:
    try:
        conn = get_connection()
        with conn:
            conn.execute(
                "INSERT INTO students (username, password, full_name, email, program, phone, notes) "
                "VALUES (:username, :password, :full_name, :email, :program, :phone, :notes)",
                payload,
            )
        return None
    except Exception as exc:
        return str(exc)


def update_student(username: str, updates: Dict[str, str]) -> Optional[str]:
    if not updates:
        return None
    try:
        assignments = ", ".join(f"{key} = :{key}" for key in updates)
        updates["username"] = username
        conn = get_connection()
        with conn:
            conn.execute(f"UPDATE students SET {assignments} WHERE username = :username", updates)
        return None
    except Exception as exc:
        return str(exc)


def delete_student(username: str) -> Optional[str]:
    return safe_db_execute("DELETE FROM students WHERE username = ?", (username,))


def fetch_student_notes(username: str) -> List[Dict[str, str]]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT id, title, file_name, mime_type, data, uploaded_at
        FROM student_notes
        WHERE student_username = ?
        ORDER BY uploaded_at DESC, id DESC
        """,
        (username,),
    ).fetchall()
    notes: List[Dict[str, str]] = []
    for row in rows:
        note_dict = dict(row)
        note_dict["data"] = bytes(row["data"]) if row["data"] is not None else b""
        notes.append(note_dict)
    return notes


def add_student_note(username: str, title: str, uploaded_file) -> Optional[str]:
    file_bytes = uploaded_file.getvalue()
    if not file_bytes:
        return "Uploaded file is empty."
    try:
        conn = get_connection()
        with conn:
            conn.execute(
                "INSERT INTO student_notes (student_username, title, file_name, mime_type, data) "
                "VALUES (?, ?, ?, ?, ?)",
                (username, title, uploaded_file.name, uploaded_file.type or "application/octet-stream", file_bytes),
            )
        return None
    except Exception as exc:
        return str(exc)


def delete_student_note(note_id: int) -> Optional[str]:
    return safe_db_execute("DELETE FROM student_notes WHERE id = ?", (note_id,))


def mark_attendance(username: str, attendance_date: str, status: str) -> Optional[str]:
    return safe_db_execute(
        "INSERT OR REPLACE INTO attendance (student_username, attendance_date, status) VALUES (?, ?, ?)",
        (username, attendance_date, status)
    )


def fetch_attendance(username: str) -> List[Dict[str, str]]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT attendance_date, status, marked_at
        FROM attendance
        WHERE student_username = ?
        ORDER BY attendance_date DESC
        """,
        (username,),
    ).fetchall()
    return [dict(row) for row in rows]


def get_attendance_status(username: str, attendance_date: str) -> Optional[str]:
    conn = get_connection()
    row = conn.execute(
        """
        SELECT status
        FROM attendance
        WHERE student_username = ? AND attendance_date = ?
        """,
        (username, attendance_date),
    ).fetchone()
    return row["status"] if row else None


def authenticate_admin(username: str, password: str) -> Optional[str]:
    conn = get_connection()
    row = conn.execute(
        "SELECT full_name FROM admins WHERE username = ? AND password = ?",
        (username, password),
    ).fetchone()
    return row["full_name"] if row else None


def authenticate_student(username: str, password: str) -> Optional[Dict[str, str]]:
    record = fetch_student(username)
    return record if record and record["password"] == password else None


def inject_custom_css() -> None:
    st.markdown(
        """
        <style>
            .main {
                background: radial-gradient(circle at top, #eef2ff 0%, #ffffff 45%);
            }
            .stApp [data-testid="stHeader"] {
                background: linear-gradient(90deg, #4338ca, #2563eb);
                color: white;
            }
            .stButton>button {
                border-radius: 10px;
                padding: 0.5rem 1.1rem;
                font-weight: 600;
            }
            .metric-card {
                border-radius: 12px;
                background: rgba(37, 99, 235, 0.1);
                padding: 1rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state() -> None:
    init_db()
    defaults = {"authenticated": False, "role": None, "current_user": None}
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def logout() -> None:
    for key in ["authenticated", "role", "current_user"]:
        st.session_state[key] = None if key != "authenticated" else False
    st.rerun()


def render_login() -> None:
    st.title("SK Python Classes")
    st.subheader("Student Management App")
    st.caption("Fast-track your progress with real-time academic tracking.")

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submitted = st.form_submit_button("Log In")

    if not submitted:
        return

    # Try admin authentication
    admin_name = authenticate_admin(username, password)
    if admin_name:
        st.session_state.update({"authenticated": True, "role": "admin", "current_user": admin_name})
        st.success(f"Welcome back, {admin_name}!")
        st.rerun()
        return

    # Try student authentication
    student_record = authenticate_student(username, password)
    if student_record:
        st.session_state.update({"authenticated": True, "role": "student", "current_user": username})
        st.success(f"Welcome back, {student_record['full_name']}!")
        st.rerun()
        return

    st.error("Invalid username or password. Please try again.")


def render_admin_dashboard() -> None:
    st.title("Administrator Dashboard")
    st.caption("Manage student records and view program information.")

    overview_tab, add_tab, manage_tab, notes_tab = st.tabs(
        ["Overview", "Add Student", "Manage Students", "Academic Notes"]
    )

    with overview_tab:
        students = fetch_students()
        if students:
            df = pd.DataFrame(students).set_index("username")
            df = df.drop(columns=["notes"], errors="ignore")
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No students are registered yet.")

    with add_tab:
        st.subheader("Register a New Student")
        with st.form("add_student_form", clear_on_submit=True):
            new_username = st.text_input("Username", placeholder="Unique login ID (e.g. 'jdoe')")
            new_password = st.text_input("Password", placeholder="Temporary password")
            full_name = st.text_input("Full Name")
            email = st.text_input("Email")
            program = st.text_input("Program")
            phone = st.text_input("Phone Number", placeholder="e.g. (555) 010-0000")
            add_submitted = st.form_submit_button("Add Student")

        if add_submitted:
            if not new_username or not new_password:
                st.error("Username and password are required.")
            elif fetch_student(new_username):
                st.error("That username is already in use.")
            else:
                error = add_student(
                    {
                        "username": new_username,
                        "password": new_password,
                        "full_name": full_name or "Unnamed Student",
                        "email": email or "Not provided",
                        "program": program or "Undeclared",
                        "phone": phone,
                        "notes": "",
                    }
                )
                if error:
                    st.error(f"Could not add student: {error}")
                else:
                    st.success(f"Student '{new_username}' added successfully.")
                    st.rerun()

    with manage_tab:
        st.subheader("Update or Remove Student")
        students = fetch_students()
        if students:
            usernames = [student["username"] for student in students]
            selected_username = st.selectbox("Choose a student", usernames, key="edit_student_select")
            if selected_username:
                selected_student = fetch_student(selected_username)
                if not selected_student:
                    st.error("Unable to load that student record.")
                else:
                    with st.form("update_student_form"):
                        edit_full_name = st.text_input("Full Name", value=selected_student["full_name"])
                        edit_email = st.text_input("Email", value=selected_student["email"])
                        edit_program = st.text_input("Program", value=selected_student["program"])
                        edit_phone = st.text_input(
                            "Phone Number", value=selected_student.get("phone") or ""
                        )
                        edit_notes = st.text_area("Notes", value=selected_student.get("notes") or "")
                        edit_password = st.text_input(
                            "Set New Password (leave blank to keep current)",
                            type="password",
                            value="",
                            placeholder="Optional",
                        )
                        update_submitted = st.form_submit_button("Save Changes")

                    if update_submitted:
                        updates = {
                            "full_name": edit_full_name,
                            "email": edit_email,
                            "program": edit_program,
                            "phone": edit_phone,
                            "notes": edit_notes,
                        }
                        if edit_password:
                            updates["password"] = edit_password
                        error = update_student(selected_username, updates)
                        if error:
                            st.error(f"Could not update record: {error}")
                        else:
                            st.success(f"Updated record for '{selected_username}'.")
                            st.rerun()

                    if st.button("Delete Selected Student", type="primary"):
                        error = delete_student(selected_username)
                        if error:
                            st.error(f"Could not delete student: {error}")
                        else:
                            st.warning(f"Student '{selected_username}' has been removed.")
                            st.rerun()
        else:
            st.info("No students available to edit or delete.")

    with notes_tab:
        st.subheader("Academic Notes Library")
        st.info("📌 Notes uploaded here will be visible to students in their 'Academic Documents' section.")
        students = fetch_students()
        
        if not students:
            st.info("Add students first to manage their academic notes.")
        else:
            # Upload section
            upload_mode = st.radio("Upload Mode", 
                ["Upload for All Students", "Upload for Specific Student"],
                key="notes_upload_mode", horizontal=True)
            
            note_title = st.text_input("Note Title", 
                placeholder="e.g. Midterm Review Packet, Course Syllabus", key="note_title_general")
            uploaded_note = st.file_uploader("Upload Note File",
                type=["pdf", "doc", "docx", "txt", "png", "jpg", "jpeg"], key="note_uploader_general")
            
            # Upload for all or specific student
            if upload_mode == "Upload for All Students":
                if st.button("Upload Academic Note for All Students", type="primary", key="upload_all_btn"):
                    if not uploaded_note:
                        st.error("Please choose a file before uploading.")
                    else:
                        title_to_use = note_title.strip() or uploaded_note.name
                        success, error = 0, 0
                        for student in students:
                            uploaded_note.seek(0)
                            if add_student_note(student["username"], title_to_use, uploaded_note):
                                error += 1
                            else:
                                success += 1
                        
                        msg = f"Academic note uploaded for all {success} students!" if error == 0 else f"Uploaded for {success} students, {error} failed."
                        (st.success if error == 0 else st.warning)(msg)
                        st.rerun()
            else:
                selected_username = st.selectbox("Choose a student",
                    [s["username"] for s in students], key="notes_student_select")
                
                if selected_username and (selected_student := fetch_student(selected_username)):
                    st.markdown(f"**{selected_student['full_name']}** &middot; {selected_student['program']}", 
                        unsafe_allow_html=True)
                    if st.button("Upload Academic Note", key=f"upload_note_btn_{selected_username}", type="primary"):
                        if not uploaded_note:
                            st.error("Please choose a file before uploading.")
                        else:
                            title_to_use = note_title.strip() or uploaded_note.name
                            error = add_student_note(selected_username, title_to_use, uploaded_note)
                            (st.error(f"Could not upload note: {error}") if error else 
                             (st.success("Academic note uploaded successfully."), st.rerun()))
            
            # View notes section
            st.divider()
            st.write("### View Student Notes")
            selected_username_view = st.selectbox("Choose a student to view their notes",
                [s["username"] for s in students], key="notes_view_student_select")
            
            if selected_username_view and (selected_student_view := fetch_student(selected_username_view)):
                st.markdown(f"**{selected_student_view['full_name']}** &middot; {selected_student_view['program']}", 
                    unsafe_allow_html=True)
                attachments = fetch_student_notes(selected_username_view)
                
                if attachments:
                    st.write(f"#### Existing Notes ({len(attachments)} total)")
                    for note in attachments:
                        col_info, col_actions = st.columns([4, 1])
                        with col_info:
                            st.write(f"**{note['title']}**")
                            st.caption(f"Uploaded: {note['uploaded_at']}")
                        with col_actions:
                            st.download_button("Download", data=note["data"],
                                file_name=note["file_name"], mime=note["mime_type"],
                                key=f"download_note_{note['id']}")
                            if st.button("Delete", key=f"delete_note_{note['id']}", help="Remove this note"):
                                error = delete_student_note(note["id"])
                                (st.error(f"Could not delete note: {error}") if error else 
                                 (st.warning("Note deleted."), st.rerun()))
                else:
                    st.info("No uploaded notes for this student yet.")

    st.divider()
    if st.button("Log Out"):
        logout()


def render_attendance_calendar(username: str, year: int, month: int) -> None:
    """Render a calendar showing attendance for the given month."""
    attendance_records = fetch_attendance(username)
    attendance_dict = {record["attendance_date"]: record["status"] for record in attendance_records}
    
    month_days = cal.Calendar().monthdayscalendar(year, month)
    st.markdown(f"### 📅 Attendance Calendar - {cal.month_name[month]} {year}")
    
    # Day headers
    cols = st.columns(7)
    for idx, day_name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
        with cols[idx]:
            st.markdown(f"**{day_name}**")
    
    # Calendar days
    for week in month_days:
        cols = st.columns(7)
        for idx, day in enumerate(week):
            with cols[idx]:
                if day == 0:
                    st.markdown("<div style='height: 60px;'></div>", unsafe_allow_html=True)
                else:
                    date_str = f"{year}-{month:02d}-{day:02d}"
                    status = attendance_dict.get(date_str, "unmarked")
                    colors = ATTENDANCE_COLORS.get(status, ATTENDANCE_COLORS["unmarked"])
                    
                    st.markdown(f"""
                        <div style='background-color: {colors["bg"]}; border-radius: 8px; padding: 10px;
                            text-align: center; height: 60px; display: flex; flex-direction: column;
                            justify-content: center; align-items: center;
                            color: {"white" if status != "unmarked" else "#6b7280"}; font-weight: bold;'>
                            <div style='font-size: 16px;'>{day}</div>
                            <div style='font-size: 12px;'>{colors["label"]}</div>
                        </div>
                        """, unsafe_allow_html=True)
    
    # Legend
    st.markdown("---")
    legend_cols = st.columns(3)
    for idx, (label, emoji) in enumerate([("Present", "🟢"), ("Absent", "🔴"), ("Not Marked", "⚪")]):
        with legend_cols[idx]:
            st.markdown(f"{emoji} **{label}**")


def render_student_dashboard(username: str) -> None:
    record = fetch_student(username)

    st.title("Student Dashboard")
    
    if not record:
        st.error("We could not find your student record. Please contact the administrator.")
        if st.button("Log Out"):
            logout()
        return

    st.success(f"Welcome, {record['full_name']}!")

    # Create tabs for different sections
    profile_tab, attendance_tab, notes_tab = st.tabs(["📋 Profile", "📅 Attendance", "📚 Documents"])

    # Profile Tab
    with profile_tab:
        edit_flag_key = f"edit_contact_{username}"
        if edit_flag_key not in st.session_state:
            st.session_state[edit_flag_key] = False

        header_cols = st.columns([6, 1])
        with header_cols[1]:
            if st.button("✏️", help="Edit contact details", key=f"edit_contact_btn_{username}"):
                st.session_state[edit_flag_key] = not st.session_state[edit_flag_key]

        st.subheader("Profile")
        st.container().markdown(
            f"""
            <div class="metric-card">
                <strong>Program</strong><br>{record['program']}
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("### Contact")
        phone_display = (record.get("phone") or "").strip() or "Not provided"
        st.write(f"**Email:** {record['email']}")
        st.write(f"**Phone:** {phone_display}")

        if st.session_state[edit_flag_key]:
            with st.form(f"student_contact_update_{username}"):
                new_email = st.text_input("Email", value=record["email"])
                new_phone = st.text_input("Phone Number", value=record.get("phone", ""))
                save_contact = st.form_submit_button("Save Contact Info")

            if save_contact:
                updates = {
                    "email": new_email or "Not provided",
                    "phone": new_phone,
                }
                error = update_student(username, updates)
                if error:
                    st.error(f"Could not update contact information: {error}")
                else:
                    st.success("Contact information updated.")
                    st.rerun()

    # Attendance Tab
    with attendance_tab:
        st.subheader("Mark Your Attendance")
        
        today = date.today()
        today_str = today.strftime("%Y-%m-%d")
        today_status = get_attendance_status(username, today_str)
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        # Mark Present/Absent buttons
        for col, (status_type, label, btn_type) in zip([col1, col2], 
                [("present", "✓ Mark Present", "primary"), ("absent", "✗ Mark Absent", "secondary")]):
            with col:
                if st.button(label, type=btn_type, use_container_width=True, disabled=today_status is not None):
                    error = mark_attendance(username, today_str, status_type)
                    if error:
                        st.error(f"Could not mark attendance: {error}")
                    else:
                        (st.success if status_type == "present" else st.warning)(f"{label.split()[0]} Marked!")
                        st.rerun()
        
        # Display today's status
        with col3:
            if today_status:
                colors = ATTENDANCE_COLORS[today_status]
                status_display = f"{today_status.title()} {colors['icon']}"
                st.markdown(
                    f"<div style='padding: 10px; background-color: {colors['light_bg']}; "
                    f"border-radius: 8px; text-align: center; font-weight: bold; "
                    f"color: {'green' if today_status == 'present' else 'red'};'>"
                    f"Today's Status: {status_display}</div>", unsafe_allow_html=True)
            else:
                st.info("You haven't marked attendance for today yet.")
        
        st.markdown("---")
        
        # Attendance statistics
        attendance_records = fetch_attendance(username)
        if attendance_records:
            present_count = sum(1 for r in attendance_records if r["status"] == "present")
            total_count = len(attendance_records)
            attendance_percentage = (present_count / total_count * 100) if total_count > 0 else 0
            
            for col, (label, value) in zip(st.columns(4), [
                ("Total Days", total_count), ("Present", present_count),
                ("Absent", total_count - present_count), ("Attendance %", f"{attendance_percentage:.1f}%")]):
                with col:
                    st.metric(label, value)
            
            st.markdown("---")
        
        # Calendar view
        st.subheader("Attendance Calendar")
        cal_cols = st.columns([2, 2, 1])
        
        with cal_cols[0]:
            selected_month = st.selectbox("Month", range(1, 13),
                format_func=lambda x: cal.month_name[x], index=today.month - 1, key="attendance_month")
        with cal_cols[1]:
            selected_year = st.selectbox("Year", range(today.year - 1, today.year + 2),
                index=1, key="attendance_year")
        
        render_attendance_calendar(username, selected_year, selected_month)

    # Documents Tab
    with notes_tab:
        st.subheader("Academic Documents")
        uploaded_notes = fetch_student_notes(username)
        
        if uploaded_notes:
            for note in uploaded_notes:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**{note['title']}**")
                    st.caption(f"Uploaded: {note['uploaded_at']}")
                with col2:
                    st.download_button("Download", data=note["data"], file_name=note["file_name"],
                        mime=note["mime_type"], key=f"student_download_{note['id']}",
                        use_container_width=True)
        else:
            st.info("No documents uploaded yet.")

    st.divider()
    if st.button("Log Out"):
        logout()


def main() -> None:
    st.set_page_config(page_title="Student Management App", page_icon="🎓", layout="wide")
    inject_custom_css()
    init_state()

    if not st.session_state.authenticated:
        render_login()
        return

    if st.session_state.role == "admin":
        render_admin_dashboard()
    elif st.session_state.role == "student":
        render_student_dashboard(st.session_state.current_user)
    else:
        st.error("Unknown role. Please log in again.")
        if st.button("Log Out"):
            logout()


if __name__ == "__main__":
    main()
