import streamlit as st
import pandas as pd

ADMIN_CREDENTIALS = {"username": "admin", "password": "admin123"}

DEFAULT_STUDENTS = {
    "sara": {
        "password": "sara2024",
        "full_name": "Sara Hernandez",
        "email": "sara.hernandez@example.com",
        "program": "Computer Science",
        "notes": "Robotics club president.",
    },
    "dylan": {
        "password": "dylan2024",
        "full_name": "Dylan Chen",
        "email": "dylan.chen@example.com",
        "program": "Mechanical Engineering",
        "notes": "Co-op placement at Horizon Industries.",
    },
    "lina": {
        "password": "lina2024",
        "full_name": "Lina Patel",
        "email": "lina.patel@example.com",
        "program": "Business Administration",
        "notes": "Dean's list for two consecutive years.",
    },
}


def init_state() -> None:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "role" not in st.session_state:
        st.session_state.role = None
    if "current_user" not in st.session_state:
        st.session_state.current_user = None
    if "students" not in st.session_state:
        # Store as a deep copy so in-memory edits do not mutate the default dict.
        st.session_state.students = {k: v.copy() for k, v in DEFAULT_STUDENTS.items()}
        for student in st.session_state.students.values():
            student.setdefault("phone", "")
    else:
        for student in st.session_state.students.values():
            student.setdefault("phone", "")


def logout() -> None:
    st.session_state.authenticated = False
    st.session_state.role = None
    st.session_state.current_user = None
    st.rerun()


def render_login() -> None:
    st.title("SK Python Classes")
    st.subheader("Student Management App")
    st.write("Log in as an administrator or student to continue.")

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submitted = st.form_submit_button("Log In")

    if submitted:
        if username == ADMIN_CREDENTIALS["username"] and password == ADMIN_CREDENTIALS["password"]:
            st.session_state.authenticated = True
            st.session_state.role = "admin"
            st.session_state.current_user = "Administrator"
            st.success("Welcome back, admin!")
            st.rerun()
            return

        students = st.session_state.students
        if username in students and password == students[username]["password"]:
            st.session_state.authenticated = True
            st.session_state.role = "student"
            st.session_state.current_user = username
            st.success(f"Welcome back, {students[username]['full_name']}!")
            st.rerun()
            return

        st.error("Invalid username or password. Please try again.")


def render_admin_dashboard() -> None:
    st.title("Administrator Dashboard")
    st.caption("Manage student records and view program information.")

    students = st.session_state.students

    data = []
    for username, details in students.items():
        row = {"username": username}
        row.update({k: v for k, v in details.items() if k not in {"password", "gpa"}})
        data.append(row)

    if data:
        st.subheader("Current Students")
        df = pd.DataFrame(data).set_index("username")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No students are registered yet.")

    st.divider()
    st.subheader("Add a New Student")
    with st.form("add_student_form", clear_on_submit=True):
        new_username = st.text_input("Username", placeholder="Unique login ID (e.g. 'jdoe')")
        new_password = st.text_input("Password", placeholder="Temporary password")
        full_name = st.text_input("Full Name")
        email = st.text_input("Email")
        program = st.text_input("Program")
        notes = st.text_area("Notes", placeholder="Optional academic notes or achievements")
        add_submitted = st.form_submit_button("Add Student")

    if add_submitted:
        if not new_username or not new_password:
            st.error("Username and password are required.")
        elif new_username in students:
            st.error("That username is already in use.")
        else:
            students[new_username] = {
                "password": new_password,
                "full_name": full_name or "Unnamed Student",
                "email": email or "Not provided",
                "program": program or "Undeclared",
                "phone": "",
                "notes": notes.strip(),
            }
            st.success(f"Student '{new_username}' added successfully.")
            st.rerun()

    st.divider()
    st.subheader("Update or Remove Student")
    if students:
        usernames = sorted(students.keys())
        selected_username = st.selectbox("Choose a student", usernames, key="edit_student_select")
        if selected_username:
            selected_student = students[selected_username]

            with st.form("update_student_form"):
                edit_full_name = st.text_input("Full Name", value=selected_student["full_name"])
                edit_email = st.text_input("Email", value=selected_student["email"])
                edit_program = st.text_input("Program", value=selected_student["program"])
                edit_notes = st.text_area("Notes", value=selected_student["notes"])
                edit_password = st.text_input(
                    "Set New Password (leave blank to keep current)",
                    type="password",
                    value="",
                    placeholder="Optional",
                )
                update_submitted = st.form_submit_button("Save Changes")

            if update_submitted:
                selected_student["full_name"] = edit_full_name
                selected_student["email"] = edit_email
                selected_student["program"] = edit_program
                selected_student.setdefault("phone", "")
                selected_student["notes"] = edit_notes
                if edit_password:
                    selected_student["password"] = edit_password
                st.success(f"Updated record for '{selected_username}'.")
                st.rerun()

            if st.button("Delete Selected Student", type="primary"):
                del students[selected_username]
                st.warning(f"Student '{selected_username}' has been removed.")
                st.rerun()
    else:
        st.info("No students available to edit or delete.")

    st.divider()
    if st.button("Log Out"):
        logout()


def render_student_dashboard(username: str) -> None:
    students = st.session_state.students
    record = students.get(username)

    st.title("Student Dashboard")
    edit_flag_key = f"edit_contact_{username}"
    if edit_flag_key not in st.session_state:
        st.session_state[edit_flag_key] = False

    header_cols = st.columns([6, 1])
    with header_cols[1]:
        if st.button("✏️", help="Edit contact details", key=f"edit_contact_btn_{username}"):
            st.session_state[edit_flag_key] = not st.session_state[edit_flag_key]

    if not record:
        st.error("We could not find your student record. Please contact the administrator.")
        if st.button("Log Out"):
            logout()
        return

    st.success(f"Welcome, {record['full_name']}!")

    st.subheader("Profile")
    st.metric("Program", record["program"])

    st.write("### Contact")
    phone_display = record.get("phone", "").strip() or "Not provided"
    st.write(f"**Email:** {record['email']}")
    st.write(f"**Phone:** {phone_display}")

    if st.session_state[edit_flag_key]:
        with st.form(f"student_contact_update_{username}"):
            new_email = st.text_input("Email", value=record["email"])
            new_phone = st.text_input("Phone Number", value=record.get("phone", ""))
            save_contact = st.form_submit_button("Save Contact Info")

        if save_contact:
            record["email"] = new_email or "Not provided"
            record["phone"] = new_phone
            st.success("Contact information updated.")
            st.rerun()

    st.write("### Academic Notes")
    if record["notes"]:
        st.info(record["notes"])
    else:
        st.write("No notes on file.")

    st.divider()
    if st.button("Log Out"):
        logout()


def main() -> None:
    st.set_page_config(page_title="Student Management App", page_icon="🎓", layout="wide")
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
