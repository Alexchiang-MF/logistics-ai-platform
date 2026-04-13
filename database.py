import sqlite3
import os
import re
import csv
from datetime import date, timedelta


def _parse_hours(val):
    """從 '5.0小時'、'2hr'、'3' 等格式中提取數字"""
    if not val:
        return 0.0
    m = re.search(r'[\d]+\.?[\d]*', str(val))
    return float(m.group()) if m else 0.0

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "projects.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            項目編號 INTEGER,
            部門 TEXT,
            任務場景名稱 TEXT,
            開發方式 TEXT,
            節省時數_每月 TEXT,
            開發人員 TEXT,
            種子負責人 TEXT,
            直屬主管 TEXT,
            每次執行耗費時間 TEXT,
            每月執行頻率 TEXT,
            有需求人數 TEXT,
            AI用途分類 TEXT,
            推進狀態 TEXT DEFAULT '商談中',
            備註 TEXT
        );

        CREATE TABLE IF NOT EXISTS weekly_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
            week_start DATE NOT NULL,
            填寫人 TEXT NOT NULL,
            本週進度內容 TEXT NOT NULL,
            推進狀態 TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    # 舊資料庫補欄位（若已存在則忽略）
    for col_def in [
        "ALTER TABLE projects ADD COLUMN created_at DATETIME",
        "ALTER TABLE projects ADD COLUMN cancel_reason TEXT",
        "ALTER TABLE projects ADD COLUMN cancel_by TEXT",
    ]:
        try:
            conn.execute(col_def)
            conn.commit()
        except Exception:
            pass
    conn.close()


# ── 使用者管理 ────────────────────────────────────────────────────────────────

def init_users():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            display  TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            is_readonly INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    # 舊資料庫補欄位
    try:
        conn.execute("ALTER TABLE users ADD COLUMN is_readonly INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if count == 0:
        seed = [
            ('inari',       'inari',       '李筱筠', 0),
            ('adychang',    'adychang',    '張綾娟', 0),
            ('c830627',     'c830627',     '蘇柏任', 0),
            ('alexchiang',  'alexchiang',  '姜淼方', 0),
            ('tienyu',      'tienyu',      '柯典佑', 0),
            ('jerry16899',  'jerry16899',  '黃則翰', 0),
            ('kun1201',     'kun1201',     '楊裔堃', 0),
            ('lv6868',      'lv6868',      '温惠君', 0),
            ('luo',         'luo',         '駱佩妏', 0),
            ('huei',        'huei',        '蕭嘉慧', 0),
            ('avon',        'avon',        '林雅芳', 0),
            ('kelly1009',   'kelly1009',   '呂羿螢', 0),
            ('redwu',       'redwu',       '吳竑儒', 0),
            ('chinhon',     'chinhon',     '蔡承翰', 0),
            ('duck1027',    'duck1027',    '李淑芬', 0),
            ('bin.liu',     'bin.liu',     '劉宏斌', 0),
            ('mgmg.wang',   'mgmg.wang',   '王筱鎂', 0),
            ('ann5410',     'ann5410',     '蔡宥婕', 0),
            ('pisece320',   'pisece320',   '黃欣婷', 0),
            ('kinant',      'kinant',      '馬尹婕', 0),
            ('vincent',     'vincent',     '黃文呈', 0),
            ('grace',       'grace',       '李貴瑜', 0),
            ('5000xp',      '5000xp',      '余武謙', 0),
            ('alanwn',      'alanwn',      '王世輝', 0),
            ('david0403',   'david0403',   '黃冠龍', 0),
            ('l098316816',  'l098316816',  '楊凱汎', 0),
            ('yimin',       'yimin',       '郭依旻', 0),
            ('admin',       'Fme@2024',    '系統管理員', 1),
        ]
        conn.executemany(
            "INSERT INTO users (username, password, display, is_admin) VALUES (?,?,?,?)", seed
        )
    # 確保 viewer 帳號存在且 is_readonly=1
    if not conn.execute("SELECT 1 FROM users WHERE username='viewer'").fetchone():
        conn.execute(
            "INSERT INTO users (username, password, display, is_admin, is_readonly) VALUES (?,?,?,0,1)",
            ('viewer', 'viewer', '唯讀使用者')
        )
    else:
        conn.execute("UPDATE users SET is_readonly=1 WHERE username='viewer'")
        conn.commit()
    conn.close()


def get_user(username):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE username=?", (username.lower(),)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def change_password(username, new_password):
    conn = get_conn()
    conn.execute("UPDATE users SET password=? WHERE username=?", (new_password, username.lower()))
    conn.commit()
    conn.close()


def create_user(username, password, display):
    conn = get_conn()
    conn.execute(
        "INSERT INTO users (username, password, display, is_admin) VALUES (?,?,?,0)",
        (username.lower(), password, display)
    )
    conn.commit()
    conn.close()


def get_all_users_list():
    conn = get_conn()
    rows = conn.execute(
        "SELECT username, display, is_admin, is_readonly FROM users ORDER BY is_admin DESC, is_readonly, username"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── 專案查詢 ──────────────────────────────────────────────────────────────────

def get_all_projects(dept=None, status=None, dev_type=None):
    """已取消專案不在此列；用 get_cancelled_projects() 另取。"""
    conn = get_conn()
    sql = """
        SELECT p.*,
               MAX(u.week_start) AS 最新更新週
        FROM projects p
        LEFT JOIN weekly_updates u ON u.project_id = p.id
        WHERE p.推進狀態 != '已取消'
    """
    params = []
    if dept:
        if '/' in dept:          # 精確課別
            sql += " AND p.部門 = ?"
            params.append(dept)
        else:                    # 父部門 → 全部課別
            sql += " AND p.部門 LIKE ?"
            params.append(dept + '/%')
    if status:
        sql += " AND p.推進狀態 = ?"
        params.append(status)
    if dev_type:
        sql += " AND p.開發方式 = ?"
        params.append(dev_type)
    sql += " GROUP BY p.id ORDER BY p.項目編號"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_cancelled_projects(dept=None, dev_type=None):
    conn = get_conn()
    sql = "SELECT * FROM projects WHERE 推進狀態 = '已取消'"
    params = []
    if dept:
        if '/' in dept:
            sql += " AND 部門 = ?"
            params.append(dept)
        else:
            sql += " AND 部門 LIKE ?"
            params.append(dept + '/%')
    if dev_type:
        sql += " AND 開發方式 = ?"
        params.append(dev_type)
    sql += " ORDER BY 項目編號"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def cancel_project(project_id, reason, cancelled_by):
    conn = get_conn()
    conn.execute(
        "UPDATE projects SET 推進狀態='已取消', cancel_reason=?, cancel_by=? WHERE id=?",
        (reason, cancelled_by, project_id)
    )
    conn.commit()
    conn.close()


def get_project(project_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_project_status(project_id, status):
    conn = get_conn()
    conn.execute("UPDATE projects SET 推進狀態=? WHERE id=?", (status, project_id))
    conn.commit()
    conn.close()


def add_weekly_update(project_id, week_start, filler, content, status):
    conn = get_conn()
    conn.execute(
        "INSERT INTO weekly_updates (project_id, week_start, 填寫人, 本週進度內容, 推進狀態) VALUES (?,?,?,?,?)",
        (project_id, week_start, filler, content, status),
    )
    conn.execute("UPDATE projects SET 推進狀態=? WHERE id=?", (status, project_id))
    conn.commit()
    conn.close()


def get_weekly_updates(project_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM weekly_updates WHERE project_id=? ORDER BY week_start DESC, created_at DESC",
        (project_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_dashboard_data():
    conn = get_conn()

    NOT_CANCELLED = "推進狀態 != '已取消'"

    status_counts = {r["推進狀態"]: r["cnt"] for r in conn.execute(
        f"SELECT 推進狀態, COUNT(*) AS cnt FROM projects WHERE {NOT_CANCELLED} GROUP BY 推進狀態"
    ).fetchall()}

    dept_counts = [dict(r) for r in conn.execute(
        f"SELECT 部門, COUNT(*) AS cnt FROM projects WHERE {NOT_CANCELLED} GROUP BY 部門 ORDER BY cnt DESC"
    ).fetchall()]

    dev_counts = {r["開發方式"]: r["cnt"] for r in conn.execute(
        f"SELECT 開發方式, COUNT(*) AS cnt FROM projects WHERE {NOT_CANCELLED} GROUP BY 開發方式"
    ).fetchall()}

    total = conn.execute(f"SELECT COUNT(*) FROM projects WHERE {NOT_CANCELLED}").fetchone()[0]

    # This week's updates (Mon–Sun of current week), excluding cancelled projects
    this_week_updates = [dict(r) for r in conn.execute("""
        SELECT u.*, p.任務場景名稱, p.部門
        FROM weekly_updates u
        JOIN projects p ON p.id = u.project_id
        WHERE u.week_start >= date('now','weekday 0','-7 days')
          AND p.推進狀態 != '已取消'
        ORDER BY u.created_at DESC
        LIMIT 50
    """).fetchall()]

    updated_this_week = conn.execute("""
        SELECT COUNT(DISTINCT u.project_id) FROM weekly_updates u
        JOIN projects p ON p.id = u.project_id
        WHERE u.week_start >= date('now','weekday 0','-7 days')
          AND p.推進狀態 != '已取消'
    """).fetchone()[0]

    saving_rows = conn.execute(
        f"SELECT 節省時數_每月 FROM projects WHERE {NOT_CANCELLED} AND 節省時數_每月 IS NOT NULL AND 節省時數_每月 != ''"
    ).fetchall()
    total_saving = round(sum(_parse_hours(r[0]) for r in saving_rows), 1)

    recent_projects = [dict(r) for r in conn.execute(f"""
        SELECT id, 項目編號, 部門, 任務場景名稱, 開發方式, 推進狀態, created_at
        FROM projects
        WHERE {NOT_CANCELLED}
        ORDER BY id DESC
        LIMIT 8
    """).fetchall()]

    # 本週進度彙整：每專案取本週最新一筆更新，依大分類分組（排除已取消）
    proj_updates_raw = conn.execute("""
        SELECT
            p.id, p.項目編號, p.部門, p.任務場景名稱,
            u.推進狀態 AS week_status, u.本週進度內容, u.填寫人
        FROM projects p
        JOIN (
            SELECT project_id, MAX(id) AS max_id
            FROM weekly_updates
            WHERE week_start >= date('now','weekday 0','-7 days')
            GROUP BY project_id
        ) latest ON latest.project_id = p.id
        JOIN weekly_updates u ON u.id = latest.max_id
        WHERE p.推進狀態 != '已取消'
        ORDER BY p.部門, p.項目編號
    """).fetchall()

    # 取得每個專案在本週之前的最後推進狀態，用以判斷本週是否有狀態變更
    prev_statuses = {}
    for row in proj_updates_raw:
        pid = row['id']
        prev = conn.execute("""
            SELECT 推進狀態 FROM weekly_updates
            WHERE project_id = ? AND week_start < date('now','weekday 0','-7 days')
            ORDER BY week_start DESC, id DESC LIMIT 1
        """, (pid,)).fetchone()
        prev_statuses[pid] = prev['推進狀態'] if prev else None

    REGIONS = ["北區營運部", "中南區營運部", "物流推進整合部"]
    weekly_by_region = {r: [] for r in REGIONS}
    for row in proj_updates_raw:
        d = dict(row)
        dept = d.get('部門') or ''
        region = next((r for r in REGIONS if dept.startswith(r)), None)
        if not region:
            continue
        pid = d['id']
        prev_st = prev_statuses.get(pid)
        d['status_changed'] = bool(prev_st and prev_st != d['week_status'])
        d['prev_status'] = prev_st
        weekly_by_region[region].append(d)

    conn.close()
    return {
        "status_counts": status_counts,
        "dept_counts": dept_counts,
        "dev_counts": dev_counts,
        "total": total,
        "updated_this_week": updated_this_week,
        "this_week_updates": this_week_updates,
        "recent_projects": recent_projects,
        "total_saving": total_saving,
        "weekly_by_region": weekly_by_region,
    }


def get_export_data():
    """匯出用：所有非取消專案 + 本週最新一筆進度內容。"""
    conn = get_conn()
    rows = conn.execute("""
        SELECT
            p.項目編號, p.部門, p.任務場景名稱, p.AI用途分類,
            p.節省時數_每月, p.推進狀態,
            u.本週進度內容 AS 本週進度
        FROM projects p
        LEFT JOIN (
            SELECT project_id, MAX(id) AS max_id
            FROM weekly_updates
            WHERE week_start >= date('now','weekday 0','-7 days')
            GROUP BY project_id
        ) latest ON latest.project_id = p.id
        LEFT JOIN weekly_updates u ON u.id = latest.max_id
        WHERE p.推進狀態 != '已取消'
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_distinct_depts():
    conn = get_conn()
    rows = conn.execute("SELECT DISTINCT 部門 FROM projects ORDER BY 部門").fetchall()
    conn.close()
    return [r[0] for r in rows]


# ── 自動備份 ─────────────────────────────────────────────────────────────────

BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")
BACKUP_INTERVAL_DAYS = 30


def _last_backup_date():
    """讀取最後一次備份的日期。"""
    marker = os.path.join(BACKUP_DIR, ".last_backup")
    if os.path.exists(marker):
        try:
            return date.fromisoformat(open(marker).read().strip())
        except Exception:
            pass
    return None


def check_and_run_backup():
    """若距離上次備份已超過 30 天，自動執行備份。"""
    last = _last_backup_date()
    if last and (date.today() - last).days < BACKUP_INTERVAL_DAYS:
        return False
    return run_backup()


def run_backup():
    """匯出所有專案與每週紀錄為 CSV，存入 backups/ 資料夾。"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    today_str = date.today().strftime("%Y%m%d")
    conn = get_conn()

    # 專案清單
    projects = conn.execute("SELECT * FROM projects ORDER BY 項目編號").fetchall()
    if projects:
        cols = projects[0].keys()
        with open(os.path.join(BACKUP_DIR, f"projects_{today_str}.csv"), "w",
                  newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(cols)
            for r in projects:
                w.writerow([r[c] for c in cols])

    # 每週進度紀錄
    updates = conn.execute("""
        SELECT u.*, p.任務場景名稱, p.部門
        FROM weekly_updates u
        JOIN projects p ON p.id = u.project_id
        ORDER BY u.week_start DESC, u.id DESC
    """).fetchall()
    if updates:
        cols = updates[0].keys()
        with open(os.path.join(BACKUP_DIR, f"weekly_updates_{today_str}.csv"), "w",
                  newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(cols)
            for r in updates:
                w.writerow([r[c] for c in cols])

    conn.close()

    # 記錄備份日期
    with open(os.path.join(BACKUP_DIR, ".last_backup"), "w") as f:
        f.write(date.today().isoformat())

    # 清理 90 天前的舊備份
    cutoff = date.today() - timedelta(days=90)
    for fn in os.listdir(BACKUP_DIR):
        if fn.startswith(("projects_", "weekly_updates_")) and fn.endswith(".csv"):
            try:
                d = date(int(fn[-12:-8]), int(fn[-8:-6]), int(fn[-6:-4]))
                if d < cutoff:
                    os.remove(os.path.join(BACKUP_DIR, fn))
            except Exception:
                pass

    return True


def get_backup_list():
    """取得所有備份檔案清單。"""
    if not os.path.exists(BACKUP_DIR):
        return []
    files = []
    for fn in sorted(os.listdir(BACKUP_DIR), reverse=True):
        if fn.endswith(".csv"):
            path = os.path.join(BACKUP_DIR, fn)
            size_kb = round(os.path.getsize(path) / 1024, 1)
            files.append({"filename": fn, "size_kb": size_kb})
    return files


# ── PythonAnywhere 延期提醒 ──────────────────────────────────────────────────

RENEWAL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "renewal_date.txt")


def get_renewal_info():
    """回傳 (renewal_date, days_elapsed, should_warn)。"""
    if os.path.exists(RENEWAL_FILE):
        try:
            renewal = date.fromisoformat(open(RENEWAL_FILE).read().strip())
        except Exception:
            renewal = date.today()
            save_renewal_date(renewal)
    else:
        renewal = date.today()
        save_renewal_date(renewal)
    elapsed = (date.today() - renewal).days
    return renewal, elapsed, elapsed >= 80


def save_renewal_date(d=None):
    """更新延期日期（預設為今天）。"""
    if d is None:
        d = date.today()
    os.makedirs(os.path.dirname(RENEWAL_FILE), exist_ok=True)
    with open(RENEWAL_FILE, "w") as f:
        f.write(d.isoformat())


STATUSES = ["商談中", "開發中", "模板測試中", "正式啟用"]
DEV_TYPES = ["1.AI Agent", "2.系統開發", "3.自行開發"]

DEPT_TREE = {
    "北區營運部": ["理貨一課", "理貨二課", "倉儲管理課", "運務課"],
    "中南區營運部": ["大肚理貨課", "大肚運務課", "岡山營運課"],
    "物流推進整合部": ["營運指導課", "數位應用課"],
}

# 扁平化清單，格式：「北區營運部/理貨一課」
DEPT_LIST = [
    f"{region}/{course}"
    for region, courses in DEPT_TREE.items()
    for course in courses
]


def update_project_info(project_id, data: dict):
    conn = get_conn()
    conn.execute("""
        UPDATE projects SET
            任務場景名稱=?, 部門=?, 開發方式=?, 節省時數_每月=?,
            每次執行耗費時間=?, 每月執行頻率=?, 有需求人數=?,
            開發人員=?, 種子負責人=?, 直屬主管=?, AI用途分類=?, 備註=?
        WHERE id=?
    """, (
        data.get('任務場景名稱'), data.get('部門'), data.get('開發方式'), data.get('節省時數_每月'),
        data.get('每次執行耗費時間'), data.get('每月執行頻率'), data.get('有需求人數'),
        data.get('開發人員'), data.get('種子負責人'), data.get('直屬主管'),
        data.get('AI用途分類'), data.get('備註'), project_id
    ))
    conn.commit()
    conn.close()


def create_project(項目編號, 部門, 任務場景名稱, 開發方式, 節省時數,
                   開發人員, 種子負責人, 直屬主管,
                   每次執行耗費時間, 每月執行頻率, 有需求人數, AI用途分類):
    conn = get_conn()
    # 若項目編號已存在則自動遞增取最大值+1
    if not 項目編號:
        max_no = conn.execute("SELECT MAX(項目編號) FROM projects").fetchone()[0] or 0
        項目編號 = max_no + 1
    conn.execute("""
        INSERT INTO projects
            (項目編號, 部門, 任務場景名稱, 開發方式, 節省時數_每月,
             開發人員, 種子負責人, 直屬主管,
             每次執行耗費時間, 每月執行頻率, 有需求人數,
             AI用途分類, 推進狀態, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'商談中', CURRENT_TIMESTAMP)
    """, (項目編號, 部門, 任務場景名稱, 開發方式, 節省時數,
          開發人員, 種子負責人, 直屬主管,
          每次執行耗費時間, 每月執行頻率, 有需求人數, AI用途分類))
    new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return new_id
