
from werkzeug.security import generate_password_hash

print("admin:", generate_password_hash("admin123"))
print("hr1:", generate_password_hash("hr123"))
print("manager1:", generate_password_hash("mgr123"))
print("emp1:", generate_password_hash("emp123"))