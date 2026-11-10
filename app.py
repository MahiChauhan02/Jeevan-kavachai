from flask import Flask, render_template, request, redirect, url_for, flash, Response
import sqlite3, csv, io, os
from pathlib import Path
from datetime import datetime, date

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "jeevan_kavach.db"

def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def init_db():
    with get_db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS medicines(
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            dose TEXT DEFAULT '', schedule TEXT NOT NULL,
            frequency TEXT DEFAULT 'Daily', stock INTEGER DEFAULT 0,
            notes TEXT DEFAULT '', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS dose_logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT, medicine_id INTEGER,
            medicine_name TEXT NOT NULL, scheduled_date TEXT NOT NULL,
            scheduled_time TEXT NOT NULL, status TEXT NOT NULL
                CHECK(status IN ('Taken','Missed')),
            logged_at TEXT NOT NULL,
            FOREIGN KEY(medicine_id) REFERENCES medicines(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS alerts(
            id INTEGER PRIMARY KEY AUTOINCREMENT, message TEXT NOT NULL,
            created_at TEXT NOT NULL, acknowledged INTEGER DEFAULT 0
        );
        """)

def ai_insights(medicines, logs):
    """Explainable, local rule-based insights. Not a medical diagnostic model."""
    insights = []
    total = len(logs)
    taken = sum(1 for x in logs if x["status"] == "Taken")
    missed = total - taken
    adherence = round(taken * 100 / total, 1) if total else 0

    if not medicines:
        insights.append(("Start your routine", "Add your prescribed medicines and reminder times to begin tracking.", "info"))
    if total:
        if adherence >= 90:
            insights.append(("Consistent routine", f"Your recorded adherence is {adherence}%. Keep using the tracker to maintain a reliable record.", "good"))
        elif adherence >= 70:
            insights.append(("Room to improve", f"Your recorded adherence is {adherence}%. Try keeping your medicine schedule somewhere easy to see.", "info"))
        else:
            insights.append(("Routine needs attention", f"Your recorded adherence is {adherence}%. Consider discussing recurring difficulties with a healthcare professional or caregiver.", "warning"))
    if missed:
        insights.append(("Missed-dose pattern", f"{missed} missed dose entr{'y' if missed == 1 else 'ies'} recorded. Review the dates and times to see whether a reminder or routine change could help.", "warning"))
    low = [m for m in medicines if int(m["stock"] or 0) <= 3]
    if low:
        names = ", ".join(m["name"] for m in low[:3])
        insights.append(("Stock running low", f"Check the remaining supply for: {names}. Follow your usual refill process.", "warning"))
    if not insights:
        insights.append(("Your care space is ready", "As you record doses, this panel will show routine and stock observations.", "info"))
    return insights[:4]

def log_dose(medicine, status):
    now = datetime.now()
    today = date.today().isoformat()
    with get_db() as con:
        existing = con.execute("""SELECT id,status FROM dose_logs
            WHERE medicine_id=? AND scheduled_date=? AND scheduled_time=?
            ORDER BY id DESC LIMIT 1""",
            (medicine["id"], today, medicine["schedule"])).fetchone()
        if existing:
            previous = existing["status"]
            con.execute("UPDATE dose_logs SET status=?,logged_at=? WHERE id=?",
                        (status, now.isoformat(timespec="seconds"), existing["id"]))
            if previous != "Taken" and status == "Taken":
                con.execute("UPDATE medicines SET stock=MAX(stock-1,0) WHERE id=?", (medicine["id"],))
            if previous == "Taken" and status == "Missed":
                con.execute("UPDATE medicines SET stock=stock+1 WHERE id=?", (medicine["id"],))
        else:
            con.execute("""INSERT INTO dose_logs
                (medicine_id,medicine_name,scheduled_date,scheduled_time,status,logged_at)
                VALUES(?,?,?,?,?,?)""",
                (medicine["id"], medicine["name"], today, medicine["schedule"],
                 status, now.isoformat(timespec="seconds")))
            if status == "Taken":
                con.execute("UPDATE medicines SET stock=MAX(stock-1,0) WHERE id=?", (medicine["id"],))
        if status == "Missed":
            con.execute("INSERT INTO alerts(message,created_at) VALUES(?,?)",
                (f"Missed dose recorded for {medicine['name']}. Review the routine.", now.isoformat(timespec="seconds")))

@app.route("/")
def dashboard():
    today = date.today().isoformat()
    with get_db() as con:
        medicines = con.execute("SELECT * FROM medicines ORDER BY schedule,name").fetchall()
        today_logs = con.execute("SELECT * FROM dose_logs WHERE scheduled_date=?", (today,)).fetchall()
        recent_logs = con.execute("SELECT * FROM dose_logs ORDER BY logged_at DESC LIMIT 10").fetchall()
        logs = con.execute("SELECT * FROM dose_logs ORDER BY logged_at DESC LIMIT 100").fetchall()
        alerts = con.execute("SELECT * FROM alerts WHERE acknowledged=0 ORDER BY created_at DESC LIMIT 5").fetchall()
    taken = sum(x["status"] == "Taken" for x in today_logs)
    missed = sum(x["status"] == "Missed" for x in today_logs)
    total = len(logs)
    all_taken = sum(x["status"] == "Taken" for x in logs)
    adherence = round(all_taken * 100 / total, 1) if total else 0
    low_stock = [m for m in medicines if m["stock"] <= 3]
    insights = ai_insights(medicines, logs)
    return render_template("index.html", page="dashboard", medicines=medicines,
        today_taken=taken, today_missed=missed, adherence=adherence,
        low_stock=low_stock, alerts=alerts, recent_logs=recent_logs,
        insights=insights, today=date.today().strftime("%A, %d %B %Y"))

@app.route("/medicines", methods=["GET","POST"])
def medicines_page():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        schedule = request.form.get("schedule","").strip()
        if not name or not schedule:
            flash("Medicine name and reminder time are required.", "error")
        else:
            try: stock = max(0, int(request.form.get("stock","0")))
            except ValueError: stock = 0
            with get_db() as con:
                con.execute("""INSERT INTO medicines(name,dose,schedule,frequency,stock,notes,created_at)
                    VALUES(?,?,?,?,?,?,?)""", (name, request.form.get("dose","").strip(),
                    schedule, request.form.get("frequency","Daily"), stock,
                    request.form.get("notes","").strip(), datetime.now().isoformat(timespec="seconds")))
            flash("Medicine saved successfully.", "success")
        return redirect(url_for("medicines_page"))
    with get_db() as con:
        medicines = con.execute("SELECT * FROM medicines ORDER BY schedule,name").fetchall()
    return render_template("index.html", page="medicines", medicines=medicines)

@app.route("/medicines/<int:medicine_id>/edit", methods=["POST"])
def edit_medicine(medicine_id):
    name = request.form.get("name","").strip()
    schedule = request.form.get("schedule","").strip()
    try: stock = max(0, int(request.form.get("stock","0")))
    except ValueError: stock = 0
    if not name or not schedule:
        flash("Name and reminder time are required.", "error")
    else:
        with get_db() as con:
            con.execute("""UPDATE medicines SET name=?,dose=?,schedule=?,frequency=?,stock=?,notes=? WHERE id=?""",
                (name, request.form.get("dose",""), schedule, request.form.get("frequency","Daily"),
                 stock, request.form.get("notes",""), medicine_id))
        flash("Medicine updated.", "success")
    return redirect(url_for("medicines_page"))

@app.route("/medicines/<int:medicine_id>/delete", methods=["POST"])
def delete_medicine(medicine_id):
    with get_db() as con: con.execute("DELETE FROM medicines WHERE id=?", (medicine_id,))
    flash("Medicine deleted.", "success")
    return redirect(url_for("medicines_page"))

@app.route("/dose/<int:medicine_id>/<status>", methods=["POST"])
def mark_dose(medicine_id, status):
    if status not in ("Taken","Missed"):
        flash("Invalid dose status.", "error")
        return redirect(url_for("dashboard"))
    with get_db() as con:
        medicine = con.execute("SELECT * FROM medicines WHERE id=?", (medicine_id,)).fetchone()
    if medicine:
        log_dose(medicine, status)
        flash(f"{medicine['name']} marked as {status}.", "success" if status == "Taken" else "warning")
    else: flash("Medicine not found.", "error")
    return redirect(request.referrer or url_for("dashboard"))

@app.route("/history")
def history():
    status = request.args.get("status","All")
    with get_db() as con:
        if status in ("Taken","Missed"):
            logs = con.execute("SELECT * FROM dose_logs WHERE status=? ORDER BY logged_at DESC", (status,)).fetchall()
        else: logs = con.execute("SELECT * FROM dose_logs ORDER BY logged_at DESC").fetchall()
        monthly = con.execute("""SELECT substr(scheduled_date,1,7) month,COUNT(*) total,
            SUM(CASE WHEN status='Taken' THEN 1 ELSE 0 END) taken
            FROM dose_logs GROUP BY substr(scheduled_date,1,7) ORDER BY month DESC LIMIT 6""").fetchall()
    return render_template("index.html", page="history", logs=logs, status=status, monthly=monthly)

@app.route("/alerts")
def alerts_page():
    with get_db() as con: alerts = con.execute("SELECT * FROM alerts ORDER BY created_at DESC LIMIT 100").fetchall()
    return render_template("index.html", page="alerts", alerts=alerts)

@app.route("/alerts/<int:alert_id>/acknowledge", methods=["POST"])
def acknowledge_alert(alert_id):
    with get_db() as con: con.execute("UPDATE alerts SET acknowledged=1 WHERE id=?", (alert_id,))
    flash("Alert acknowledged.", "success")
    return redirect(url_for("alerts_page"))

@app.route("/tools")
def features_page():
    with get_db() as con:
        medicines = con.execute("SELECT * FROM medicines ORDER BY schedule").fetchall()
        logs = con.execute("SELECT * FROM dose_logs ORDER BY logged_at DESC LIMIT 100").fetchall()
    return render_template("index.html", page="features", medicines=medicines,
                           insights=ai_insights(medicines, logs), missed_count=sum(x["status"]=="Missed" for x in logs))

@app.route("/export.csv")
def export_csv():
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Medicine","Scheduled date","Scheduled time","Status","Logged at"])
    with get_db() as con:
        rows = con.execute("SELECT medicine_name,scheduled_date,scheduled_time,status,logged_at FROM dose_logs ORDER BY logged_at DESC").fetchall()
    writer.writerows([list(r) for r in rows])
    return Response(out.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition":"attachment; filename=jeevan_kavach_dose_history.csv"})

@app.route("/health")
def health():
    return {"status":"ok","app":"Jeevan Kavach AI"}

init_db()
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5001)))
