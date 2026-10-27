
import streamlit as st
import pandas as pd
from pymongo import MongoClient
from datetime import datetime

st.set_page_config(
    page_title="Student Management Dashboard",
    page_icon="🎓",
    layout="wide"
)

SERVERS = {
    "Bengaluru": {
        "uri": "mongodb://127.0.0.1:27017/",
        "database": "BengaluruDB"
    },
    "Mysuru": {
        "uri": "mongodb://127.0.0.1:27018/",
        "database": "MysuruDB"
    },
    "Backup": {
        "uri": "mongodb://127.0.0.1:27019/",
        "database": "StudentBackupDB"
    }
}

@st.cache_resource
def get_client(uri):
    return MongoClient(uri, serverSelectionTimeoutMS=1500)

def get_collection(server):
    config = SERVERS[server]
    client = get_client(config["uri"])
    client.admin.command("ping")
    return client[config["database"]]["students"]

def get_status(server):
    try:
        get_collection(server)
        return True
    except Exception:
        return False

def get_student(sid):
    for server in ("Bengaluru", "Mysuru"):
        if get_status(server):
            try:
                student = get_collection(server).find_one(
                    {"student_id": sid}
                )
                if student:
                    return student, server
            except Exception:
                pass
    return None, None

def sync_backup(student):
    if get_status("Backup"):
        get_collection("Backup").replace_one(
            {"student_id": student["student_id"]},
            student.copy(),
            upsert=True
        )

st.title("🎓 Student Management Dashboard")
st.caption("Distributed Student Information Management System Using MongoDB")

# Server status
st.subheader("Database Server Status")
status_cols = st.columns(3)
server_online = {}

for col, server in zip(status_cols, SERVERS):
    online = get_status(server)
    server_online[server] = online
    with col:
        st.metric(
            label=server,
            value="Online" if online else "Offline",
            delta=f"Port {SERVERS[server]['uri'].split(':')[2].split('/')[0]}"
        )

# Read student records from the two main databases
students = []
for server in ("Bengaluru", "Mysuru"):
    if server_online[server]:
        try:
            students.extend(
                list(get_collection(server).find({}, {"_id": 0}))
            )
        except Exception:
            pass

# Summary metrics
st.divider()
m1, m2, m3 = st.columns(3)
m1.metric("Total Students", len(students))
m2.metric(
    "Bengaluru Students",
    sum(s.get("branch") == "Bengaluru" for s in students)
)
m3.metric(
    "Mysuru Students",
    sum(s.get("branch") == "Mysuru" for s in students)
)

# Navigation
st.divider()
page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Add Student",
        "Search Student",
        "Update Student",
        "Delete Student"
    ]
)

if page == "Dashboard":
    st.subheader("All Student Records")

    query = st.text_input("Search by student ID, name or course")
    filtered = [
        s for s in students
        if query.lower() in " ".join([
            str(s.get("student_id", "")),
            str(s.get("name", "")),
            str(s.get("course", ""))
        ]).lower()
    ]

    if filtered:
        st.dataframe(
            pd.DataFrame(filtered),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No student records found.")

    st.caption("Records are read from the two main databases.")

elif page == "Add Student":
    st.subheader("Add New Student")

    with st.form("add_student_form"):
        sid = st.text_input("Student ID")
        name = st.text_input("Student Name")
        course = st.text_input("Course", value="MTech CSE")
        branch = st.selectbox("Branch", ["Bengaluru", "Mysuru"])
        email = st.text_input("Email")
        submitted = st.form_submit_button("Add Student")

    if submitted:
        if not all([sid.strip(), name.strip(), course.strip(), email.strip()]):
            st.error("Please fill in every field.")
        elif not server_online["Bengaluru"] or not server_online["Mysuru"]:
            st.error("Both main servers must be online to add a student.")
        elif any(s.get("student_id") == sid.strip() for s in students):
            st.error("This student ID already exists.")
        else:
            student = {
                "student_id": sid.strip(),
                "name": name.strip(),
                "course": course.strip(),
                "branch": branch,
                "email": email.strip(),
                "created_at": datetime.now().isoformat()
            }
            try:
                get_collection(branch).insert_one(student.copy())
                st.success(f"Student added to {branch} database.")

                try:
                    sync_backup(student)
                    if server_online["Backup"]:
                        st.success("Backup copy updated.")
                    else:
                        st.warning("Backup server is offline.")
                except Exception:
                    st.warning(
                        "Student saved, but the backup write failed."
                    )
            except Exception as e:
                st.error(f"Could not add student: {e}")

elif page == "Search Student":
    st.subheader("Search Student")
    sid = st.text_input("Enter Student ID")

    if st.button("Search"):
        if not sid.strip():
            st.warning("Enter a student ID.")
        else:
            student, server = get_student(sid.strip())
            if student:
                st.success(f"Student found in {server}.")
                st.json({
                    k: v for k, v in student.items() if k != "_id"
                })
            else:
                st.warning("Student not found on main servers.")

elif page == "Update Student":
    st.subheader("Update Student Email")
    sid = st.text_input("Student ID", key="update_id")
    new_email = st.text_input("New Email")

    if st.button("Update Email"):
        student, server = get_student(sid.strip())

        if not sid.strip() or not new_email.strip():
            st.warning("Enter the student ID and new email.")
        elif not student:
            st.error("Student not found.")
        else:
            try:
                get_collection(server).update_one(
                    {"student_id": sid.strip()},
                    {"$set": {"email": new_email.strip()}}
                )
                student["email"] = new_email.strip()

                try:
                    sync_backup(student)
                    st.success("Student updated; backup synchronized.")
                except Exception:
                    st.warning(
                        "Student updated, but backup synchronization failed."
                    )
            except Exception as e:
                st.error(f"Update failed: {e}")

elif page == "Delete Student":
    st.subheader("Delete Student")
    sid = st.text_input("Student ID to delete")

    confirm = st.checkbox("I confirm that I want to delete this student")

    if st.button("Delete Student", type="primary"):
        if not confirm:
            st.warning("Please confirm the deletion.")
        elif not sid.strip():
            st.warning("Enter a student ID.")
        else:
            student, server = get_student(sid.strip())

            if not student:
                st.error("Student not found on main servers.")
            else:
                try:
                    get_collection(server).delete_one(
                        {"student_id": sid.strip()}
                    )

                    if server_online["Backup"]:
                        get_collection("Backup").delete_one(
                            {"student_id": sid.strip()}
                        )

                    st.success("Student deleted from the main database.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Delete failed: {e}")

st.divider()
st.caption(
    "Academic demonstration | Python + Streamlit + MongoDB + PyMongo"
)
