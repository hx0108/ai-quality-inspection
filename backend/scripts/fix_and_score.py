import sys, bcrypt, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "/app")
from database import SessionLocal
from models.models import User
import urllib.request

db = SessionLocal()
admin = db.query(User).filter(User.role == "admin").first()

# Set a known working password
new_pwd = "Admin@2026!"
admin.password_hash = bcrypt.hashpw(new_pwd.encode(), bcrypt.gensalt()).decode()
admin.must_change_pwd = False
db.commit()

# Verify it works
test = bcrypt.checkpw(new_pwd.encode(), admin.password_hash.encode())
print("Password set and verified:", test)

# Login
body = json.dumps({"account": "admin", "password": new_pwd}).encode()
req = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1/auth/login",
    data=body,
    headers={"Content-Type": "application/json"},
    method="POST"
)
resp = urllib.request.urlopen(req)
token = json.loads(resp.read())["access_token"]
print("Login OK")

# Trigger scoring
req2 = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1/scoring/start/Q-20260312-d04fcec5",
    data=b"",
    headers={"Authorization": "Bearer " + token},
    method="POST"
)
try:
    resp2 = urllib.request.urlopen(req2)
    print("Scoring triggered:", resp2.read().decode()[:500])
except urllib.error.HTTPError as e:
    print("Scoring HTTP %d:" % e.code, e.read().decode()[:500])

# Set must_change_pwd so admin resets on next login
admin.must_change_pwd = True
db.commit()
print("Done. Admin must change password on next login.")
db.close()
