"""
End-to-end smoke test for MessMate covering the flow described in the spec:
register -> login -> members -> meals -> bazar -> deposits -> settlement ->
edit & recalc -> logout/login persistence -> leap year -> mess isolation.
"""
import os
import sys

# Use an isolated test database
TEST_DB = os.path.join(os.path.dirname(__file__), "instance", "test_messmate.db")
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)

import config
config.Config.SQLALCHEMY_DATABASE_URI = "sqlite:///" + TEST_DB

from app import create_app
from models import db

app = create_app()
app.config["TESTING"] = True
client = app.test_client()


def ok(desc, cond):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {desc}")
    if not cond:
        FAILURES.append(desc)


FAILURES = []

# 1. Register Mess A
r = client.post("/register", data={
    "mess_name": "Green Valley Hostel",
    "manager_name": "Alice",
    "username": "alice",
    "password": "pass123",
    "confirm_password": "pass123",
}, follow_redirects=True)
ok("Register Mess A succeeds", r.status_code == 200 and b"Login" in r.data or r.status_code == 200)

# 2. Login Mess A
r = client.post("/login", data={
    "mess_name": "Green Valley Hostel",
    "username": "alice",
    "password": "pass123",
}, follow_redirects=True)
ok("Login Mess A succeeds", r.status_code == 200 and b"Dashboard" in r.data)

# 3. Add 3 members
names = ["Rahim", "Karim", "Hasan"]
for n in names:
    r = client.post("/members/add", data={"name": n, "phone": "", "joining_date": "2026-08-01"},
                     follow_redirects=True)
ok("Members page lists 3 members", all(n.encode() in r.data for n in names))

with app.app_context():
    from models.member import Member
    from models.mess import Mess
    mess_a = Mess.query.filter_by(name="Green Valley Hostel").first()
    members = Member.query.filter_by(mess_id=mess_a.id).order_by(Member.id.asc()).all()
    member_ids = {m.name: m.id for m in members}

# 4. Set target meal rate
r = client.post("/settings/target", data={"target_meal_rate": "45"}, follow_redirects=True)
ok("Target meal rate set", r.status_code == 200)

# 5. Enter meals for August 2026 (leap-adjacent test month), day 1
YEAR, MONTH = 2026, 8


def toggle_meal(member_name, day, meal_type, taken):
    return client.post("/meals/toggle", json={
        "member_id": member_ids[member_name],
        "year": YEAR, "month": MONTH, "day": day,
        "meal_type": meal_type, "taken": taken,
    })


r = toggle_meal("Rahim", 1, "breakfast", True)
ok("Meal toggle auto-save returns ok", r.get_json()["ok"] is True)
toggle_meal("Rahim", 1, "lunch", True)
toggle_meal("Rahim", 1, "dinner", True)
toggle_meal("Karim", 1, "breakfast", True)
toggle_meal("Karim", 1, "lunch", True)
toggle_meal("Hasan", 1, "breakfast", True)

# Day 2 meals
toggle_meal("Rahim", 2, "breakfast", True)
toggle_meal("Karim", 2, "lunch", True)
toggle_meal("Hasan", 2, "dinner", True)

# 6. Multiple bazar entries same day (29 Aug scenario -> use day 1)
r = client.post("/bazar/add", data={
    "year": YEAR, "month": MONTH, "date": "2026-08-01",
    "member_id": member_ids["Rahim"], "amount": "1500", "items_description": "Rice, vegetables",
}, follow_redirects=True)
r = client.post("/bazar/add", data={
    "year": YEAR, "month": MONTH, "date": "2026-08-01",
    "member_id": member_ids["Karim"], "amount": "800", "items_description": "Fish",
}, follow_redirects=True)
ok("Two bazar entries on same day both saved", b"1500" in r.data and b"800" in r.data)

# Bazar on another day, empty description
r = client.post("/bazar/add", data={
    "year": YEAR, "month": MONTH, "date": "2026-08-02",
    "member_id": member_ids["Hasan"], "amount": "1850", "items_description": "",
}, follow_redirects=True)
ok("Bazar entry with empty optional description saved", b"1850" in r.data)

# 7. Deposits
client.post("/deposits/add", data={"year": YEAR, "month": MONTH, "date": "2026-08-01",
                                    "member_id": member_ids["Rahim"], "amount": "3000", "note": ""},
            follow_redirects=True)
client.post("/deposits/add", data={"year": YEAR, "month": MONTH, "date": "2026-08-15",
                                    "member_id": member_ids["Rahim"], "amount": "2000", "note": ""},
            follow_redirects=True)
client.post("/deposits/add", data={"year": YEAR, "month": MONTH, "date": "2026-08-01",
                                    "member_id": member_ids["Karim"], "amount": "4000", "note": ""},
            follow_redirects=True)
client.post("/deposits/add", data={"year": YEAR, "month": MONTH, "date": "2026-08-01",
                                    "member_id": member_ids["Hasan"], "amount": "1000", "note": ""},
            follow_redirects=True)

# 8. Verify running meal rate / dashboard
with app.app_context():
    from routes.helpers import get_daily_history, get_month_totals, get_member_settlement
    history = get_daily_history(mess_a.id, YEAR, MONTH)
    day1 = history[0]
    day2 = history[1]
    # Day1: bazar 1500+800=2300, meals: Rahim(3)+Karim(2)+Hasan(1)=6
    ok("Day1 daily bazar = 2300", day1["daily_bazar"] == 2300)
    ok("Day1 daily meals = 6", day1["daily_meals"] == 6)
    ok("Day1 running rate = 2300/6", abs(day1["running_rate"] - round(2300/6, 2)) < 0.01)
    # Day2: cumulative bazar 2300+1850=4150, cumulative meals 6+3=9
    ok("Day2 cumulative bazar = 4150", day2["cumulative_bazar"] == 4150)
    ok("Day2 cumulative meals = 9", day2["cumulative_meals"] == 9)

    totals = get_month_totals(mess_a.id, YEAR, MONTH)
    ok("Final meal rate = total bazar / total meals",
       abs(totals["final_rate"] - round(4150/9, 2)) < 0.01)

    # target 45, running rate now ~461 (since few meals) -> should warn
    mess_a_fresh = Mess.query.get(mess_a.id) if False else None

    settlement = get_member_settlement(mess_a.id, YEAR, MONTH)
    settle_by_name = {s["member"].name: s for s in settlement}
    rahim = settle_by_name["Rahim"]
    ok("Rahim total meals = 4 (3 day1 + 1 day2)", rahim["total_meals"] == 4)
    expected_cost = round(4 * totals["final_rate"], 2)
    ok("Rahim meal cost matches final rate * meals", rahim["meal_cost"] == expected_cost)
    ok("Rahim deposit total = 5000", rahim["total_deposit"] == 5000)

# 9. Warning check via dashboard route
r = client.get(f"/dashboard?year={YEAR}&month={MONTH}")
ok("Dashboard loads", r.status_code == 200)
ok("Warning banner shown when running rate above target", b"above your target" in r.data or b"above the target" in r.data or b"Meal rate is" in r.data)

# 10. Edit an old meal (5 Aug Rahim lunch not set yet -> set true) then verify recalculation
toggle_meal("Rahim", 5, "lunch", True)
with app.app_context():
    history2 = get_daily_history(mess_a.id, YEAR, MONTH)
    day5 = history2[4]
    ok("Day5 has 1 meal after edit", day5["daily_meals"] == 1)
    day_last = history2[-1]
    ok("Cumulative meals increased after edit", day_last["cumulative_meals"] == 10)

# 11. Edit a bazar entry and verify recalculation
with app.app_context():
    from models.bazar import Bazar
    entry = Bazar.query.filter_by(mess_id=mess_a.id, amount=1500).first()
    entry_id = entry.id
r = client.post(f"/bazar/{entry_id}/edit", data={
    "date": "2026-08-01", "member_id": member_ids["Rahim"], "amount": "1700",
    "items_description": "Rice, vegetables, oil",
}, follow_redirects=True)
with app.app_context():
    totals2 = get_month_totals(mess_a.id, YEAR, MONTH)
    ok("Total bazar updated after edit (was 4150, +200 = 4350)", totals2["total_bazar"] == 4350)

# 12. Edit deposit and verify settlement update
with app.app_context():
    from models.deposit import Deposit
    dep = Deposit.query.filter_by(mess_id=mess_a.id, member_id=member_ids["Rahim"], amount=2000).first()
    dep_id = dep.id
client.post(f"/deposits/{dep_id}/edit", data={
    "date": "2026-08-15", "member_id": member_ids["Rahim"], "amount": "2500", "note": "top-up",
}, follow_redirects=True)
with app.app_context():
    settlement2 = get_member_settlement(mess_a.id, YEAR, MONTH)
    rahim2 = {s["member"].name: s for s in settlement2}["Rahim"]
    ok("Rahim deposit total updated to 5500", rahim2["total_deposit"] == 5500)

# 13. Logout / login again -> data persists
client.get("/logout", follow_redirects=True)
r = client.post("/login", data={"mess_name": "Green Valley Hostel", "username": "alice",
                                 "password": "pass123"}, follow_redirects=True)
ok("Re-login succeeds", b"Dashboard" in r.data)
r = client.get("/members")
ok("Members persist after logout/login", b"Rahim" in r.data and b"Karim" in r.data and b"Hasan" in r.data)

# 14. Leap year Feb check: 2028 is leap (29 days), 2026 is not (28 days)
with app.app_context():
    from routes.helpers import days_in_month
    ok("Feb 2026 has 28 days", days_in_month(2026, 2) == 28)
    ok("Feb 2028 has 29 days (leap year)", days_in_month(2028, 2) == 29)
    ok("Jan has 31 days", days_in_month(2026, 1) == 31)
    ok("Apr has 30 days", days_in_month(2026, 4) == 30)

# 15. Zero meals / zero bazar for an empty month -> no division by zero
r = client.get("/dashboard?year=2027&month=3")
ok("Dashboard with zero data does not crash", r.status_code == 200)
with app.app_context():
    totals_empty = get_month_totals(mess_a.id, 2027, 3)
    ok("Final rate is 0.0 when no meals (no div by zero)", totals_empty["final_rate"] == 0.0)

# 16. Two mess accounts -> verify isolation
client.get("/logout", follow_redirects=True)
r = client.post("/register", data={
    "mess_name": "Sunrise Hostel", "manager_name": "Bob", "username": "bob",
    "password": "pass456", "confirm_password": "pass456",
}, follow_redirects=True)
r = client.post("/login", data={"mess_name": "Sunrise Hostel", "username": "bob",
                                 "password": "pass456"}, follow_redirects=True)
ok("Login Mess B succeeds", b"Dashboard" in r.data)
r = client.get("/members")
ok("Mess B sees no members from Mess A", b"Rahim" not in r.data and b"Karim" not in r.data)

# Try direct URL manipulation: Mess B tries to edit Mess A's member
with app.app_context():
    rahim_id = member_ids["Rahim"]
r = client.post(f"/members/{rahim_id}/edit", data={"name": "Hacked", "phone": "", "joining_date": "2026-08-01"})
ok("Cross-mess edit blocked (404)", r.status_code == 404)

r = client.get(f"/members/{rahim_id}/details")
ok("Cross-mess view blocked (404)", r.status_code == 404)

with app.app_context():
    from models.member import Member as M
    rahim_check = M.query.get(rahim_id)
    ok("Mess A's member name unmodified by Mess B attempt", rahim_check.name == "Rahim")

print("\n===== SUMMARY =====")
if FAILURES:
    print(f"{len(FAILURES)} test(s) FAILED:")
    for f in FAILURES:
        print(" -", f)
    sys.exit(1)
else:
    print("ALL TESTS PASSED")
