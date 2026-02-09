from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename

import matplotlib
matplotlib.use("Agg")
from openpyxl import Workbook
from flask import send_file
from flask import Flask, request,render_template,redirect,session,url_for
import mysql.connector

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "static/uploads"

app.secret_key = "secret123"


# ---------------- DATABASE CONNECTION ----------------
db = mysql.connector.connect(
    user="root",
    password="root123",
    database="ems_db",
    unix_socket="/tmp/mysql.sock"
)

#--------role check-----------
def role_required(allowed_roles):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if "user" not in session:
                return redirect("/login")
            if session["role"] not in allowed_roles:
                return "Access Denied", 403
            return func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator


# ---------------- HOME PAGE ----------------
@app.route("/")
def home():
    return render_template("home.html")

# ---------------- ADD EMPLOYEE ----------------
@app.route("/add", methods=["POST"])
@role_required(["HR", "Admin"])
def add_employee():
    if "user" not in session:
        return redirect("/login")
    name = request.form["name"]
    email = request.form["email"]
    department = request.form["department"]
    salary = int(request.form["salary"])
    photo = request.files["photo"]
    filename = secure_filename(photo.filename)
    photo.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO employees (name, email,department, salary,photo) VALUES (%s, %s, %s, %s, %s)",
        (name, email, department,salary,filename)
    )
    db.commit()
    return "Employee Added Successfully! <br><a href='/'>Back</a>"
# --    -------------- VIEW EMPLOYEES ----------------
@app.route("/view")
@role_required(["HR", "Manager", "Admin"])
def view_employees():
    if "user" not in session:
        return redirect("/login")
    cursor = db.cursor()
    cursor.execute("SELECT * FROM employees")
    employees = cursor.fetchall()

    return render_template("view.html",employees=employees)
#------Search______-----
@app.route("/search", methods=["POST"])
def search_employee():
    keyword = request.form["keyword"]

    cursor = db.cursor()
    cursor.execute(
        "SELECT * FROM employees WHERE name LIKE %s",
        ("%" + keyword + "%",)
    )
    employees = cursor.fetchall()

    return render_template("view.html", employees=employees)


# ---------------- DELETE EMPLOYEE ----------------
@app.route("/delete/<int:id>")
@role_required(["Admin"])
def delete_employee(id):
    if "user" not in session:
        return redirect("/login")
    cursor = db.cursor()
    cursor.execute("DELETE FROM employees WHERE id=%s", (id,))
    db.commit()

    return "Employee Deleted Successfully! <br><a href='/view'>Back</a>"

# ---------------- EDIT EMPLOYEE ----------------
@app.route("/edit/<int:id>")
@role_required(["HR", "Admin"])
def edit_employee(id):
    if "user" not in session:
        return redirect("/login")
    cursor = db.cursor()
    cursor.execute("SELECT * FROM employees WHERE id=%s", (id,))
    emp = cursor.fetchone()

    return render_template("edit.html",emp=emp)

# ---------------- UPDATE EMPLOYEE ----------------
@app.route("/update/<int:id>", methods=["POST"])
@role_required(["HR", "Admin"])
def update_employee(id):
    if "user" not in session:
        return redirect("/login")
    name = request.form["name"]
    email = request.form["email"]
    department = request.form["department"]

    salary = int(request.form["salary"])

    cursor = db.cursor()
    cursor.execute(
        "UPDATE employees SET name=%s, email=%s, department=%s,salary=%s WHERE id=%s",
        (name, email, department,salary, id)
    )
    db.commit()

    return "Employee Updated Successfully! <br><a href='/view'>Back</a>"

#_____________login_________________
@app.route("/login", methods=["GET","POST"])
def login():
    msg = ""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT users.*, roles.role_name 
            FROM users 
            JOIN roles ON users.role_id = roles.id
            WHERE username=%s
        """, (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user["password"],password):
            session["user"] = user["username"]
            session["role"] = user["role_name"]
            session["user_id"] = user["id"]
            return redirect("/dashboard")
        else:
            msg = "Invalid Login"

    return render_template("login.html", msg=msg)


#----logout-------

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

#----export-------
@app.route("/export")
@role_required(["HR", "Admin"])
def export_excel():
    if "user" not in session:
        return redirect("/login")

    cursor = db.cursor()
    cursor.execute("SELECT * FROM employees")
    data = cursor.fetchall()

    wb = Workbook()
    sheet = wb.active
    sheet.title = "Employees"

    sheet.append(["ID", "Name", "Email", "Salary"])

    for row in data:
        sheet.append(row)

    file_name = "employees.xlsx"
    wb.save(file_name)

    return send_file(file_name, as_attachment=True)

#---------Dashboard------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    cursor = db.cursor()

    cursor.execute("SELECT COUNT(*) FROM employees")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT AVG(salary) FROM employees")
    avg_salary = cursor.fetchone()[0]

    cursor.execute("SELECT MAX(salary) FROM employees")
    max_salary = cursor.fetchone()[0]

    cursor.execute("SELECT MIN(salary) FROM employees")
    min_salary = cursor.fetchone()[0]

    return render_template(
        "dashboard.html",
        total=total,
        avg=avg_salary,
        max=max_salary,
        min=min_salary
    )

#------salary chart--------
import matplotlib.pyplot as plt

@app.route("/salary_chart")
def salary_chart():
    if "user" not in session:
        return redirect("/login")
    cursor = db.cursor()
    cursor.execute("SELECT name, salary FROM employees")
    data = cursor.fetchall()

    names = [row[0] for row in data]
    salaries = [row[1] for row in data]

    import matplotlib.pyplot as plt

    plt.figure()
    plt.bar(names, salaries)
    plt.xlabel("Employees")
    plt.ylabel("Salary")
    plt.title("Employee Salary Chart")
    plt.xticks(rotation=45)
    plt.tight_layout()

    plt.savefig("static/salary.png")
    plt.close()

    return send_file("static/salary.png", mimetype="image/png")

#------
@app.route("/my_profile")
@role_required(["Employee", "Admin", "HR"])
def my_profile():
    cursor = db.cursor()
    cursor.execute(
        "SELECT * FROM employees WHERE user_id = %s",
        (session["user_id"],)
    )
    emp = cursor.fetchone()
    return render_template("my_profile.html", emp=emp)





# ---------------- RUN SERVER ----------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
