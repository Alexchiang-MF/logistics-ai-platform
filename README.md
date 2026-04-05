# 物流本部 AI 開發管理平台

> 統一追蹤與管理物流本部各單位 AI 專案推進進度的內部平台。

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python) ![Flask](https://img.shields.io/badge/Flask-3.0-lightgrey?logo=flask) ![License](https://img.shields.io/badge/License-Private-red)

---

## 專案簡介

本平台為物流本部內部使用的 AI 專案管理系統，提供各單位種子人員一個統一的介面，用於登錄、追蹤及回報 AI 工具的開發與導入進度。

主要功能涵蓋：
- 各部門 AI 專案的新增、查閱與狀態更新
- 每週進度填寫與彙整
- 節省工時的自動計算與統計
- 管理者總覽 Dashboard

---

## 功能特色

### Dashboard 總覽
- **節省時數合計**：自動加總所有專案每月節省的工作時數
- **推進狀態分布**：圓餅圖呈現商談中 / 開發中 / 模板測試中 / 正式啟用的比例
- **各部門項目數**：橫條圖顯示各課室負責的 AI 專案數量
- **最近新增專案**：快速檢視最新登錄的專案項目

### 專案管理
- 支援 AI Agent、自行開發等多種開發方式分類
- 記錄任務場景、直屬主管、種子負責人等關鍵資訊
- 每月執行頻次 × 每次耗時 → 自動計算節省時數

### 每週進度追蹤
- 種子人員每週填寫進度摘要與推進狀態
- 歷史紀錄可供查閱與回溯

### 帳號與權限
| 角色 | 權限 |
|------|------|
| 登入用戶 | 新增專案、填寫進度、更新狀態 |
| 訪客 | 唯讀，僅能瀏覽資料 |

---

## 技術架構

| 層級 | 技術 |
|------|------|
| 後端框架 | Python Flask |
| 資料庫 | SQLite |
| 前端 UI | Bootstrap 5 + Bootstrap Icons |
| 圖表 | Chart.js |
| 部署 | PythonAnywhere |

---

## 本地安裝與執行

```bash
# 1. 複製專案
git clone https://github.com/Alexchiang-MF/logistics-ai-platform.git
cd logistics-ai-platform

# 2. 建立虛擬環境
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # macOS/Linux

# 3. 安裝套件
pip install -r requirements.txt

# 4. 啟動開發伺服器
python app.py
```

開啟瀏覽器前往 `http://localhost:5000`

---

## 預設帳號

| 帳號 | 顯示名稱 |
|------|----------|
| alexchiang | 姜淼方 |
| inari | 李筱筠 |
| adychang | 張綾娟 |
| c830627 | 蘇柏任 |

---

## 線上版本

本平台已部署至 PythonAnywhere：
🔗 [https://alexchiang.pythonanywhere.com](https://alexchiang.pythonanywhere.com)

---

## 開發單位

物流本部 · 推進整合部
AI 種子計畫 — 內部工具開發
