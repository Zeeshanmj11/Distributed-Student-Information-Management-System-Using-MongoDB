
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# Connect to the three MongoDB servers
blr_client = MongoClient(
    "mongodb://127.0.0.1:27017/",
    serverSelectionTimeoutMS=3000
)
mys_client = MongoClient(
    "mongodb://127.0.0.1:27018/",
    serverSelectionTimeoutMS=3000
)
backup_client = MongoClient(
    "mongodb://127.0.0.1:27019/",
    serverSelectionTimeoutMS=3000
)

# Select databases and collections
blr_db = blr_client["BengaluruDB"]
mys_db = mys_client["MysuruDB"]
backup_db = backup_client["StudentBackupDB"]

blr_students = blr_db["students"]
mys_students = mys_db["students"]
backup_students = backup_db["students"]


def connect_servers():
    try:
        blr_client.admin.command("ping")
        mys_client.admin.command("ping")
        backup_client.admin.command("ping")
        print("All three MongoDB servers connected!")
        return True
    except PyMongoError as error:
        print("Connection error:", error)
        return False


def get_primary_collection(student_id):
    # Even-numbered IDs go to Bengaluru; odd go to Mysuru
    last_digit = int(student_id[-1])

    if last_digit % 2 == 0:
        return blr_students, "BengaluruDB"
    return mys_students, "MysuruDB"


def find_student(student_id):
    student = blr_students.find_one({"student_id": student_id})

    if student is None:
        student = mys_students.find_one({"student_id": student_id})

    return student


def add_student():
    student_id = input("Enter student ID: ").strip()

    if not student_id or not student_id[-1].isdigit():
        print("Student ID must end with a digit.")
        return

    if find_student(student_id):
        print("Student ID already exists!")
        return

    name = input("Enter student name: ").strip()
    course = input("Enter course: ").strip()
    branch = input("Enter branch: ").strip()
    email = input("Enter email: ").strip()

    if not all([name, course, branch, email]):
        print("All fields are required.")
        return

    student = {
        "student_id": student_id,
        "name": name,
        "course": course,
        "branch": branch,
        "email": email
    }

    try:
        primary, database_name = get_primary_collection(student_id)
        primary.insert_one(student.copy())
        backup_students.replace_one(
            {"student_id": student_id},
            student.copy(),
            upsert=True
        )

        print("Student added successfully!")
        print("Primary database:", database_name)
        print("Backup copy created on server 3.")

    except PyMongoError as error:
        print("Database error:", error)
        print("Check both the primary and backup databases.")


def view_students():
    try:
        print("\n--- BENGALURU STUDENTS ---")
        for student in blr_students.find().sort("student_id", 1):
            print(student)

        print("\n--- MYSURU STUDENTS ---")
        for student in mys_students.find().sort("student_id", 1):
            print(student)

    except PyMongoError as error:
        print("Database error:", error)


def search_student():
    student_id = input("Enter student ID to search: ").strip()

    try:
        student = find_student(student_id)

        if student:
            print("\nStudent found:")
            print(student)
        else:
            print("Student not found.")

    except PyMongoError as error:
        print("Database error:", error)


def update_student():
    student_id = input("Enter student ID to update: ").strip()

    try:
        student = find_student(student_id)

        if not student:
            print("Student not found.")
            return

        print("Leave a field empty to keep its current value.")
        name = input("New name: ").strip()
        course = input("New course: ").strip()
        branch = input("New branch: ").strip()
        email = input("New email: ").strip()

        changes = {}
        if name:
            changes["name"] = name
        if course:
            changes["course"] = course
        if branch:
            changes["branch"] = branch
        if email:
            changes["email"] = email

        if not changes:
            print("No changes entered.")
            return

        primary, _ = get_primary_collection(student_id)
        primary.update_one(
            {"student_id": student_id},
            {"$set": changes}
        )

        backup_students.update_one(
            {"student_id": student_id},
            {"$set": changes}
        )

        print("Student updated successfully!")
        print("Backup copy updated.")

    except PyMongoError as error:
        print("Database error:", error)


def delete_student():
    student_id = input("Enter student ID to delete: ").strip()

    try:
        student = find_student(student_id)

        if not student:
            print("Student not found.")
            return

        primary, _ = get_primary_collection(student_id)
        primary.delete_one({"student_id": student_id})
        backup_students.delete_one({"student_id": student_id})

        print("Student deleted from primary and backup databases.")

    except PyMongoError as error:
        print("Database error:", error)


def main():
    if not connect_servers():
        print("Start all three MongoDB servers and try again.")
        return

    while True:
        print("\n================================")
        print("DISTRIBUTED STUDENT MANAGEMENT")
        print("================================")
        print("1. Add student")
        print("2. View all students")
        print("3. Search student")
        print("4. Update student")
        print("5. Delete student")
        print("6. Exit")

        choice = input("Enter your choice (1-6): ").strip()

        if choice == "1":
            add_student()
        elif choice == "2":
            view_students()
        elif choice == "3":
            search_student()
        elif choice == "4":
            update_student()
        elif choice == "5":
            delete_student()
        elif choice == "6":
            print("Student Management System closed.")
            break
        else:
            print("Invalid choice. Enter a number from 1 to 6.")

    blr_client.close()
    mys_client.close()
    backup_client.close()


if __name__ == "__main__":
    main()