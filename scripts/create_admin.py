"""Create the initial administrator from a trusted terminal; safe to rerun is intentionally not assumed."""
import getpass
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from sqlalchemy import select
from app.core.security import hash_password
from app.database import Base, SessionLocal, engine
from app.models import Admin

Base.metadata.create_all(bind=engine)
username = input("Admin username: ").strip()
if not username:
    sys.exit("Username cannot be empty")
password = getpass.getpass("Password (12+ characters): ")
confirm = getpass.getpass("Confirm password: ")
if password != confirm:
    sys.exit("Passwords do not match")
try:
    encoded = hash_password(password)
except ValueError as exc:
    sys.exit(str(exc))
with SessionLocal() as db:
    if db.scalar(select(Admin).where(Admin.username == username)):
        sys.exit("That username already exists; no changes made")
    db.add(Admin(username=username, password_hash=encoded, is_superadmin=True))
    db.commit()
print("Administrator created successfully.")
