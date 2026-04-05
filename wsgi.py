"""
PythonAnywhere WSGI 入口檔
部署步驟：將此檔案內容貼到 PythonAnywhere 的 WSGI 設定頁面
（記得把 YOUR_USERNAME 換成你的帳號名稱）
"""
import sys
import os

# 修改為你在 PythonAnywhere 上的專案路徑
PROJECT_PATH = '/home/YOUR_USERNAME/ai-platform'

if PROJECT_PATH not in sys.path:
    sys.path.insert(0, PROJECT_PATH)

os.chdir(PROJECT_PATH)

from app import app as application
