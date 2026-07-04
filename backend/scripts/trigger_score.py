import sys, bcrypt, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "/app")
from database import SessionLocal
from models.models import User
from api.auth import verify_password
import urllib.request

db = SessionLocal()
admin = db.query(User).filter(User.role == "admin").first()

# Set temp password
temp_pwd = "Sc0ring!Temp"
admin.password_hash = bcrypt.hashpw(temp_pwd.encode(), bcrypt.gensalt()).decode()
admin.must_change_pwd = False
db.commit()
print("Temp password set")

# Login via urllib
body = json.dumps({"account": "admin", "password": temp_pwd}).encode()
req = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1/auth/login",
    data=body,
    headers={"Content-Type": "application/json"},
    method="POST"
)
resp = urllib.request.urlopen(req)
login_data = json.loads(resp.read())
token = login_data["access_token"]
print("Login OK")

# Restore password
admin.password_hash = bcrypt.hashpw("hx0108035118?".encode(), bcrypt.gensalt()).decode()
admin.must_change_pwd = True
db.commit()
print("Password restored (must change on next login)")
db.close()

# Trigger scoring
req2 = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1/scoring/start/Q-20260312-d04fcec5",
    data=b"",
    headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
    method="POST"
)
try:
    resp2 = urllib.request.urlopen(req2)
    print("Scoring triggered:", resp2.read().decode()[:500])
except urllib.error.HTTPError as e:
    print("Scoring HTTP %d:" % e.code, e.read().decode()[:500])
