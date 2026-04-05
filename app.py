import os
from datetime import date, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session
import database as db

app = Flask(__name__)
app.secret_key = "ai-platform-2024"

db.init_db()

USERS = {
    'inari':      {'password': 'inari',      'display': '李筱筠'},
    'adychang':   {'password': 'adychang',   'display': '張綾娟'},
    'c830627':    {'password': 'c830627',    'display': '蘇柏任'},
    'alexchiang': {'password': 'alexchiang', 'display': '姜淼方'},
}


def get_current_user():
    if session.get('username'):
        u = USERS.get(session['username'])
        if u:
            return {'username': session['username'], 'display': u['display'], 'is_guest': False}
    if session.get('is_guest'):
        return {'username': 'guest', 'display': '訪客', 'is_guest': True}
    return None


@app.context_processor
def inject_user():
    return dict(current_user=get_current_user())


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not get_current_user():
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def require_login(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return redirect(url_for('login'))
        if user['is_guest']:
            flash('訪客無法執行此操作，請登入後再試', 'warning')
            return redirect(request.referrer or url_for('projects'))
        return f(*args, **kwargs)
    return decorated


def this_monday():
    today = date.today()
    return (today - timedelta(days=today.weekday())).isoformat()


# ── Auth ───────────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if get_current_user():
        return redirect(url_for('dashboard'))
    if request.method == "POST":
        action = request.form.get('action')
        if action == 'guest':
            session.clear()
            session['is_guest'] = True
            return redirect(url_for('dashboard'))
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        user = USERS.get(username)
        if user and user['password'] == password:
            session.clear()
            session['username'] = username
            return redirect(url_for('dashboard'))
        flash('帳號或密碼錯誤', 'danger')
    return render_template('login.html')


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))


# ── Dashboard ──────────────────────────────────────────────────────────────────

@app.route("/")
@require_auth
def dashboard():
    data = db.get_dashboard_data()
    return render_template("dashboard.html", data=data, statuses=db.STATUSES)


@app.route("/api/dashboard")
@require_auth
def api_dashboard():
    return jsonify(db.get_dashboard_data())


# ── Project List ───────────────────────────────────────────────────────────────

@app.route("/projects")
@require_auth
def projects():
    dept = request.args.get("dept", "")
    status = request.args.get("status", "")
    dev_type = request.args.get("dev_type", "")
    items = db.get_all_projects(
        dept=dept or None,
        status=status or None,
        dev_type=dev_type or None,
    )
    return render_template(
        "projects.html",
        projects=items,
        dept_tree=db.DEPT_TREE,
        dept_list=db.DEPT_LIST,
        statuses=db.STATUSES,
        dev_types=db.DEV_TYPES,
        selected_dept=dept,
        selected_status=status,
        selected_dev_type=dev_type,
    )


@app.route("/projects/new", methods=["POST"])
@require_login
def project_new():
    def f(key):
        return request.form.get(key, "").strip()

    部門 = f("部門")
    任務場景名稱 = f("任務場景名稱")
    if not 部門 or not 任務場景名稱:
        flash("部門/課別與任務場景名稱為必填", "warning")
        return redirect(url_for("projects"))

    new_id = db.create_project(
        項目編號=None,
        部門=部門,
        任務場景名稱=任務場景名稱,
        開發方式=f("開發方式") or "1.AI Agent",
        節省時數=f("節省時數_每月"),
        開發人員=f("開發人員"),
        種子負責人=f("種子負責人"),
        直屬主管=f("直屬主管"),
        每次執行耗費時間=f("每次執行耗費時間"),
        每月執行頻率=f("每月執行頻率"),
        有需求人數=f("有需求人數"),
        AI用途分類=f("AI用途分類"),
    )
    flash(f"任務「{任務場景名稱}」已新增", "success")
    return redirect(url_for("project_detail", pid=new_id))


# ── Project Detail ─────────────────────────────────────────────────────────────

@app.route("/project/<int:pid>")
@require_auth
def project_detail(pid):
    project = db.get_project(pid)
    if not project:
        flash("找不到此專案", "danger")
        return redirect(url_for("projects"))
    updates = db.get_weekly_updates(pid)
    return render_template(
        "project_detail.html",
        project=project,
        updates=updates,
        statuses=db.STATUSES,
        this_monday=this_monday(),
    )


@app.route("/project/<int:pid>/update", methods=["POST"])
@require_login
def project_update(pid):
    week_start = request.form.get("week_start", this_monday())
    filler = request.form.get("填寫人", "").strip()
    content = request.form.get("本週進度內容", "").strip()
    status = request.form.get("推進狀態", "商談中")

    if not filler or not content:
        flash("填寫人與本週進度內容為必填", "warning")
        return redirect(url_for("project_detail", pid=pid))

    db.add_weekly_update(pid, week_start, filler, content, status)
    flash("進度已儲存", "success")
    return redirect(url_for("project_detail", pid=pid))


@app.route("/project/<int:pid>/status", methods=["POST"])
@require_login
def project_status(pid):
    status = request.form.get("推進狀態")
    if status in db.STATUSES:
        db.update_project_status(pid, status)
        flash(f"狀態已更新為「{status}」", "success")
    return redirect(url_for("project_detail", pid=pid))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(debug=debug, host="0.0.0.0", port=port)
