"""
Targeted test: confirms there is NO 30-member cap. Adds 35 members to a
fresh mess and verifies member #31-#35 are created and usable.
Run standalone: python test_unlimited_members.py
"""
import os
import sys

TEST_DB = os.path.join(os.path.dirname(__file__), "instance", "test_unlimited_members.db")
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)

import config
config.Config.SQLALCHEMY_DATABASE_URI = "sqlite:///" + TEST_DB

from app import create_app

app = create_app()
app.config["TESTING"] = True
client = app.test_client()

FAILURES = []


def ok(desc, cond):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {desc}")
    if not cond:
        FAILURES.append(desc)


client.post("/register", data={
    "mess_name": "Big Hostel", "manager_name": "Owner", "username": "owner",
    "password": "pass123", "confirm_password": "pass123",
}, follow_redirects=True)
client.post("/login", data={"mess_name": "Big Hostel", "username": "owner",
                             "password": "pass123"}, follow_redirects=True)

TOTAL = 35
for i in range(1, TOTAL + 1):
    r = client.post("/members/add", data={
        "name": f"Member{i:03d}", "phone": "", "joining_date": "2026-08-01",
    }, follow_redirects=True)
    if r.status_code != 200:
        ok(f"Add member #{i} returns 200", False)

r = client.get("/members")
ok(f"All {TOTAL} members appear on Members page (beyond the old 30 cap)",
   all(f"Member{i:03d}".encode() in r.data for i in range(1, TOTAL + 1)))
ok("Member #31 specifically exists", b"Member031" in r.data)
ok("Member #35 specifically exists", b"Member035" in r.data)

with app.app_context():
    from models.member import Member
    from models.mess import Mess
    mess = Mess.query.filter_by(name="Big Hostel").first()
    count = Member.query.filter_by(mess_id=mess.id).count()
    ok(f"Database contains exactly {TOTAL} members (no silent truncation)", count == TOTAL)

# Confirm member #31 works normally in the meals grid too
r = client.get("/meals?year=2026&month=8")
ok("Meals grid renders successfully with 35 members", r.status_code == 200)
ok("Member #31 appears in the meals grid", b"Member031" in r.data)

print("\n===== SUMMARY =====")
if FAILURES:
    print(f"{len(FAILURES)} test(s) FAILED:")
    for f in FAILURES:
        print(" -", f)
    sys.exit(1)
else:
    print("ALL TESTS PASSED — no 30-member limit exists.")
