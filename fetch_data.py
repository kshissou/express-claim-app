# fetch_data.py - 每 6 小时自动抓取快递数据并更新主表

import requests
from bs4 import BeautifulSoup
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ---------------- 配置区域 ----------------
SPREADSHEET_NAME = "快递包裹自动同步"
MAIN_SHEET = "Sheet1"
CREDENTIALS_FILE = "credentials.json"

URL = "http://www.yuanriguoji.com/Phone/Package?WaveHouse=0&Prediction=2&Storage=0&Grounding=0&active=1"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Cookie": "ClientData=xxxxxx"  # 替换为你的实际 Cookie
}
# ----------------------------------------

def get_gsheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scope)
    client = gspread.authorize(creds)
    return client

def update_main_sheet(df):
    client = get_gsheet()
    sheet = client.open(SPREADSHEET_NAME).worksheet(MAIN_SHEET)
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

def fetch_packages():
    res = requests.get(URL, headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")

    packages = soup.find_all("input", class_="chk_select")
    records = []

    for pkg in packages:
        weight = pkg.get("data-weight", "").strip()
        pkg_id = pkg.get("value", "").strip()
        tracking_span = soup.find("span", {"name": "BillCode", "data-id": pkg_id})
        tracking_number = tracking_span.text.strip() if tracking_span else ""

        if tracking_number and weight:
            records.append({
                "快递单号": tracking_number,
                "重量（kg）": weight
            })

    return pd.DataFrame(records)

def main():
    print("[定时任务] 正在抓取最新快递数据...")
    df = fetch_packages()
    print(f"抓取到 {len(df)} 条记录，正在更新主表...")
    update_main_sheet(df)
    print("主表更新完成 ✅")

if __name__ == "__main__":
    main()
