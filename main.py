from flask import Flask, request, render_template
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os
import json
import tempfile

app = Flask(__name__)

# ==== 配置 ====
SPREADSHEET_NAME = "express-claim-app"
MAIN_SHEET = "Sheet1"
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

@app.route("/", methods=["GET", "POST"])
def index():
    message = None
    result = None

    if request.method == "POST":
        print("🔥 收到 POST 请求")
        tracking = request.form.get("tracking", "").strip()
        nickname = request.form.get("nickname", "").strip()
        print(f"✅ 用户输入的 tracking: {tracking}")
        print(f"✅ 用户输入的 nickname: {nickname}")

        try:
            client = get_gsheet()
            print("🧪 成功连接 Google Sheets")
            sheet = client.open(SPREADSHEET_NAME).worksheet(MAIN_SHEET)
            data = sheet.get_all_records()
            print(f"📄 读取表格数据，共 {len(data)} 条记录")
            df = pd.DataFrame(data)
            print("🔍 表格列名:", df.columns.tolist())

            if df.empty:
                message = "❌ 表格为空，无法查询"
                print("⚠️ 表格是空的")
            elif tracking in df["快递单号"].astype(str).values:
                matched = df[df["快递单号"].astype(str) == tracking].iloc[0]
                print(f"📦 找到匹配单号: {matched.to_dict()}")

                if nickname:
