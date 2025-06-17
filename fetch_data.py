import requests
from bs4 import BeautifulSoup
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os
import json
import tempfile

# ==== 配置 ====
SPREADSHEET_NAME = "express-claim-app"
MAIN_SHEET = "Sheet1"
URL = "http://www.yuanriguoji.com/Phone/Package?WaveHouse=0&Prediction=2&Storage=0&Grounding=0&active=1"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Cookie": "ClientData=你的clientdata"  # 替换为你抓到的 Cookie
}
# ==============

def get_gsheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    json_str = os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"]
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
        tmp.write(json_str)
        tmp.flush()
        creds = Credentials.from_service_account_file(tmp.name, scopes=scopes)
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
                "重量（kg）": weight,
                "谁的快递": ""
            })

    return pd.DataFrame(records)

def main():
    print("[定时任务] 抓取快递数据中...")
    df = fetch_packages()
    print(f"共抓取 {len(df)} 条记录")
    update_main_sheet(df)
    print("✅ Google Sheets 主表已更新")

if __name__ == "__main__":
    main()
