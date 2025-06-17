from flask import Flask, render_template, request, redirect
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from bs4 import BeautifulSoup
import requests

# ---------------- 配置区域 ----------------
SPREADSHEET_NAME = "快递包裹自动同步"
MAIN_SHEET = "Sheet1"
CREDENTIALS_FILE = "credentials.json"

# 抓取数据相关
URL = "http://www.yuanriguoji.com/Phone/Package?WaveHouse=0&Prediction=2&Storage=0&Grounding=0&active=1"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Cookie": "ClientData=xxxxxx"  # 替换为你的实际 Cookie
}
# ----------------------------------------

app = Flask(__name__)

def get_gsheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scope)
    client = gspread.authorize(creds)
    return client

def get_main_sheet():
    client = get_gsheet()
    sheet = client.open(SPREADSHEET_NAME).worksheet(MAIN_SHEET)
    return sheet

def read_sheet_df():
    sheet = get_main_sheet()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    return df

def update_main_sheet(df):
    sheet = get_main_sheet()
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

def update_user_sheets(df):
    client = get_gsheet()
    users = df["谁的快递"].dropna().unique()
    for user in users:
        user_df = df[df["谁的快递"] == user][["快递单号", "重量（kg）"]]
        total_weight = user_df["重量（kg）"].astype(float).sum()
        user_df.loc[len(user_df.index)] = ["总计", total_weight]
        try:
            sheet = client.open(SPREADSHEET_NAME).worksheet(user)
        except:
            sheet = client.open(SPREADSHEET_NAME).add_worksheet(title=user, rows="100", cols="2")
        sheet.clear()
        sheet.update([user_df.columns.values.tolist()] + user_df.values.tolist())

@app.route("/", methods=["GET", "POST"])
def index():
    message = ""
    df = read_sheet_df()
    result = None

    if request.method == "POST":
        tracking_number = request.form.get("tracking")
        nickname = request.form.get("nickname")

        # 查找记录
        if tracking_number in df["快递单号"].values:
            df.loc[df["快递单号"] == tracking_number, "谁的快递"] = nickname
            update_main_sheet(df)
            update_user_sheets(df)
            message = f"成功认领：{tracking_number} 给 {nickname}"
        else:
            message = "未找到该快递单号"

    if request.args.get("q"):
        q = request.args.get("q")
        result = df[df["快递单号"].astype(str).str.contains(q)]

    return render_template("index.html", result=result, message=message)

if __name__ == "__main__":
    app.run(debug=True)
