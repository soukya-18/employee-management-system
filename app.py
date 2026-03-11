import mysql.connector
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from flask import Flask, request, render_template, redirect, session, url_for, send_file, flash
from openpyxl import Workbook
from io import BytesIO
from functools import wraps

# ---------------- LOAD ENV ----------------
load_dotenv()

# ---------------- DATABASE ----------------
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Root@123",
    database="ems_db"
)

cursor = db.cursor(dictionary=True, buffered=True)


# ---------------- FLASK ----------------
app = Flask(__name__)
app.secret_key = "ems_secret"

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- LOGIN REQUIRED ----------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return wrapper


# ---------------- ROLE CHECK ----------------
def role_required(roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if session.get("role") not in roles:
                flash("Access denied", "danger")
                return redirect("/")
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ---------------- HOME ----------------
@app.route("/")
@login_required
def home():

    role = session.get("role")

    if role in ["Admin","HR"]:
        return redirect("/dashboard")

    if role == "Manager":
        return redirect("/employees")

    if role == "Employee":
        return redirect("/my_profile")

    return redirect("/login")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        cursor.execute("""
        SELECT u.id,u.username,u.password,r.role_name,e.id as emp_id
        FROM users u
        LEFT JOIN roles r ON u.role_id=r.id
        LEFT JOIN employees e ON e.user_id=u.id
        WHERE username=%s
        """,(username,))

        user = cursor.fetchone()

        if user and check_password_hash(user["password"],password):

            session["user_id"] = user["id"]
            session["user"] = user["username"]
            session["role"] = user["role_name"]
            session["employee_id"] = user["emp_id"]

            flash("Login successful","success")
            return redirect("/")

        flash("Invalid login","danger")

    return render_template("login.html")


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():

    session.clear()
    return redirect("/login")


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
@login_required
@role_required(["Admin","HR"])
def dashboard():

    cursor.execute("SELECT COUNT(*) as total FROM employees")
    total = cursor.fetchone()["total"]

    cursor.execute("SELECT AVG(salary) as avg FROM employees")
    avg = cursor.fetchone()["avg"] or 0

    cursor.execute("SELECT MAX(salary) as max FROM employees")
    max_salary = cursor.fetchone()["max"] or 0

    cursor.execute("SELECT MIN(salary) as min FROM employees")
    min_salary = cursor.fetchone()["min"] or 0

    cursor.execute("SELECT * FROM employees ORDER BY id DESC LIMIT 5")
    recent = cursor.fetchall()

    return render_template(
        "dashboard.html",
        total=total,
        avg=round(avg,2),
        max=max_salary,
        min=min_salary,
        recent=recent
    )


# ---------------- EMPLOYEES PAGE ----------------
@app.route("/employees")
@login_required
@role_required(["Admin","HR","Manager"])
def employees():

    cursor.execute("SELECT * FROM employees ORDER BY id DESC")
    employees = cursor.fetchall()

    return render_template("employees.html",employees=employees)

@app.route('/search_employee', methods=['POST'])
@login_required
@role_required(["Admin","HR","Manager"])
def search_employee():
    keyword = request.form.get("keyword")

    cursor = db.cursor(dictionary=True)

    query = """
    SELECT * FROM employees
    WHERE name LIKE %s
    OR department LIKE %s
    OR email LIKE %s
    """

    cursor.execute(query, (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"))
    employees = cursor.fetchall()

    return render_template("employees.html", employees=employees)

# ---------------- ADD EMPLOYEE ----------------
@app.route("/add_employee", methods=["GET","POST"])
@login_required
@role_required(["Admin","HR"])
def add_employee():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        department = request.form["department"]
        salary = request.form["salary"]
        role_id = request.form["role"]   # <-- NEW

        username = email

        default_password = "emp123"

        hashed_password = generate_password_hash(default_password)

        cursor.execute("""
        INSERT INTO users (username,password,role_id)
        VALUES (%s,%s,%s)
        """,(username,hashed_password,role_id))

        user_id = cursor.lastrowid

        photo = request.files["photo"]
        filename = None

        if photo and photo.filename != "":
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        # insert employee
        cursor.execute("""
        INSERT INTO employees(name,email,department,salary,photo,user_id)
        VALUES(%s,%s,%s,%s,%s,%s)
        """,(name,email,department,salary,filename,user_id))

        db.commit()
        flash(f"Employee added successfully. Username: {email} | Password: emp123","success")

        return redirect("/employees")

    return render_template("add_employee.html")
# ---------------- EDIT EMPLOYEE ----------------
@app.route("/edit_employee/<int:id>",methods=["GET","POST"])
@login_required
@role_required(["Admin","HR"])
def edit_employee(id):

    cursor.execute("""
    SELECT e.*, u.role_id 
    FROM employees e
    JOIN users u ON e.user_id = u.id
    WHERE e.id=%s
    """,(id,))
    emp = cursor.fetchone()

    if request.method=="POST":

        name=request.form["name"]
        email=request.form["email"]
        department=request.form["department"]
        salary=request.form["salary"]
        role_id=request.form["role"]   # NEW

        photo=request.files["photo"]
        filename=emp["photo"]

        if photo and photo.filename!="":
            filename=secure_filename(photo.filename)
            photo.save(os.path.join(app.config["UPLOAD_FOLDER"],filename))

        # update employee table
        cursor.execute("""
        UPDATE employees
        SET name=%s,email=%s,department=%s,salary=%s,photo=%s
        WHERE id=%s
        """,(name,email,department,salary,filename,id))

        # update role in users table
        cursor.execute("""
        UPDATE users
        SET role_id=%s
        WHERE id=%s
        """,(role_id,emp["user_id"]))

        db.commit()

        flash("Employee updated successfully","success")
        return redirect("/employees")

    return render_template("edit.html",emp=emp)

# ---------------- DELETE ----------------
@app.route("/delete_employee/<int:id>")
@login_required
@role_required(["Admin","HR"])
def delete_employee(id):

    cursor.execute("SELECT user_id FROM employees WHERE id=%s",(id,))
    emp = cursor.fetchone()

    cursor.execute("DELETE FROM employees WHERE id=%s",(id,))
    cursor.execute("DELETE FROM users WHERE id=%s",(emp["user_id"],))

    db.commit()
    flash("Employee deleted","danger")
    return redirect("/employees")



# ---------------- PROFILE ----------------
@app.route("/my_profile")
@login_required
def my_profile():

    user_id = session.get("user_id")

    cursor.execute("""
    SELECT e.*, r.role_name
    FROM users u
    LEFT JOIN employees e ON u.id = e.user_id
    LEFT JOIN roles r ON u.role_id = r.id
    WHERE u.id=%s
    """,(user_id,))

    emp = cursor.fetchone()

    return render_template("my_profile.html", emp=emp)

@app.route("/change_password", methods=["GET","POST"])
@login_required
def change_password():

    if request.method == "POST":

        current_password = request.form["current_password"]
        new_password = request.form["new_password"]

        user_id = session["user_id"]

        cursor.execute("SELECT password FROM users WHERE id=%s",(user_id,))
        user = cursor.fetchone()

        if not check_password_hash(user["password"], current_password):
            flash("Current password is incorrect","danger")
            return redirect("/change_password")

        new_hash = generate_password_hash(new_password)

        cursor.execute(
            "UPDATE users SET password=%s WHERE id=%s",
            (new_hash,user_id)
        )

        db.commit()

        flash("Password changed successfully","success")
        return redirect("/")

    return render_template("change_password.html")


# ---------------- EXPORT EXCEL ----------------
@app.route("/export_excel")
@login_required
@role_required(["Admin","HR"])
def export_excel():

    cursor.execute("SELECT * FROM employees")
    data=cursor.fetchall()

    wb=Workbook()
    sheet=wb.active

    sheet.append(["ID","Name","Email","Department","Salary"])

    for row in data:
        sheet.append([row["id"],row["name"],row["email"],row["department"],row["salary"]])

    output=BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(output,as_attachment=True,download_name="employees.xlsx")


# ---------------- SALARY CHART ----------------
@app.route("/salary_chart")
@login_required
def salary_chart():

    cursor.execute("SELECT name,salary FROM employees")
    data=cursor.fetchall()

    names=[x["name"] for x in data]
    salaries=[x["salary"] for x in data]

    plt.bar(names,salaries)
    plt.xticks(rotation=45)

    img=BytesIO()
    plt.savefig(img,format="png")
    img.seek(0)
    plt.close()

    return send_file(img,mimetype="image/png")


# ---------------- RUN ----------------
if __name__=="__main__":
    app.run(debug=True)