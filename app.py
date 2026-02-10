from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename

import matplotlib
matplotlib.use("Agg")

from flask import (
    Flask,
    request,
    render_template,
    redirect,
    session,
    url_for,
    send_file
)

# ---------------- APP SETUP ----------------
app = Flask(__name__)
app.secret_key = "secret123"
app.config["UPLOAD_FOLDER"] = "static/uploads"

# ---------------- DATABASE (TEMP DISABLED) ----------------
db = None  # IMPORTANT: DB disabled for Render deployment


def db_disabled():
    return "🚧 Database temporarily disabled. App is live on Render.", 503


# ---------------- ROLE CHECK ----------------
def role_required(allowed_roles):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if "user" not in session:
                return redirect("/login")
            if session.get("role") not in allowed_roles:
                return "Access Denied", 403
            return func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator


# ---------------- HOME ----------------
@app.route("/")
def home():
    return """
    <h1>🚀 Employee Management System</h1>
    <p>Successfully deployed on Render</p>
    <p>Database features are temporarily disabled.</p>
    """


# ---------------- LOGIN (DISABLED) ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    return """
    <h2>Login Disabled</h2>
    <p>Database not connected yet.</p>
    """


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ---------------- DASHBOARD (DISABLED) ----------------
@app.route("/dashboard")
def dashboard():
    return db_disabled()


# ---------------- ADD EMPLOYEE ----------------
@app.route("/add", methods=["POST"])
@role_required(["HR", "Admin"])
def add_employee():
    return db_disabled()


# ---------------- VIEW EMPLOYEES ----------------
@app.route("/view")
@role_required(["HR", "Manager", "Admin"])
def view_employees():
    return db_disabled()


# ---------------- SEARCH ----------------
@app.route("/search", methods=["POST"])
def search_employee():
    return db_disabled()


# ---------------- DELETE ----------------
@app.route("/delete/<int:id>")
@role_required(["Admin"])
def delete_employee(id):
    return db_disabled()


# ---------------- EDIT ----------------
@app.route("/edit/<int:id>")
@role_required(["HR", "Admin"])
def edit_employee(id):
    return db_disabled()


# ---------------- UPDATE ----------------
@app.route("/update/<int:id>", methods=["POST"])
@role_required(["HR", "Admin"])
def update_employee(id):
    return db_disabled()


# ---------------- EXPORT ----------------
@app.route("/export")
@role_required(["HR", "Admin"])
def export_excel():
    return db_disabled()


# ---------------- SALARY CHART ----------------
@app.route("/salary_chart")
def salary_chart():
    return db_disabled()


# ---------------- MY PROFILE ----------------
@app.route("/my_profile")
@role_required(["Employee", "Admin", "HR"])
def my_profile():
    return db_disabled()


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)



