"""
從 總表.xlsx 匯入專案資料到 SQLite。
可重複執行（依項目編號 upsert）。
"""
import os
import sqlite3
import openpyxl

import sys

# 可傳入 Excel 路徑作為第一個參數，否則預設找同目錄下的 總表.xlsx
if len(sys.argv) > 1:
    EXCEL_PATH = sys.argv[1]
else:
    EXCEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "總表.xlsx")

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "projects.db")


def clean(val):
    if val is None:
        return ""
    return str(val).strip()


def main():
    from database import init_db
    init_db()

    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    ws = wb.active

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    imported = 0
    skipped = 0

    for row in ws.iter_rows(min_row=2, values_only=True):
        項目編號 = row[0]
        if 項目編號 is None:
            continue
        try:
            項目編號 = int(項目編號)
        except (ValueError, TypeError):
            continue

        部門 = clean(row[1])
        任務場景名稱 = clean(row[2])
        # row[3] = 維持/開發狀態 (V / 新增) — 用作備註，不是推進狀態
        原始狀態 = clean(row[3])
        開發方式_raw = clean(row[4])
        # 標準化開發方式
        if "1" in 開發方式_raw or "AI Agent" in 開發方式_raw:
            開發方式 = "1.AI Agent"
        elif "2" in 開發方式_raw or "系統" in 開發方式_raw:
            開發方式 = "2.系統開發"
        else:
            開發方式 = "3.自行開發"

        節省時數 = clean(row[5])
        開發人員 = clean(row[6])
        種子負責人 = clean(row[7])
        直屬主管 = clean(row[8])
        每次執行耗費時間 = clean(row[9])
        每月執行頻率 = clean(row[10])
        有需求人數 = clean(row[11])
        AI用途分類 = clean(row[17]) if len(row) > 17 else ""
        備註 = f"原始狀態：{原始狀態}"

        existing = conn.execute(
            "SELECT id FROM projects WHERE 項目編號=?", (項目編號,)
        ).fetchone()

        if existing:
            conn.execute("""
                UPDATE projects SET
                    部門=?, 任務場景名稱=?, 開發方式=?, 節省時數_每月=?,
                    開發人員=?, 種子負責人=?, 直屬主管=?,
                    每次執行耗費時間=?, 每月執行頻率=?, 有需求人數=?,
                    AI用途分類=?, 備註=?
                WHERE 項目編號=?
            """, (部門, 任務場景名稱, 開發方式, 節省時數,
                  開發人員, 種子負責人, 直屬主管,
                  每次執行耗費時間, 每月執行頻率, 有需求人數,
                  AI用途分類, 備註, 項目編號))
            skipped += 1
        else:
            conn.execute("""
                INSERT INTO projects
                    (項目編號, 部門, 任務場景名稱, 開發方式, 節省時數_每月,
                     開發人員, 種子負責人, 直屬主管,
                     每次執行耗費時間, 每月執行頻率, 有需求人數,
                     AI用途分類, 推進狀態, 備註)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'商談中',?)
            """, (項目編號, 部門, 任務場景名稱, 開發方式, 節省時數,
                  開發人員, 種子負責人, 直屬主管,
                  每次執行耗費時間, 每月執行頻率, 有需求人數,
                  AI用途分類, 備註))
            imported += 1

    conn.commit()
    conn.close()
    print(f"完成：新增 {imported} 筆，更新 {skipped} 筆")


if __name__ == "__main__":
    main()
