from flask import Flask, request, render_template
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os

app = Flask(__name__)

# ==== 配置区域 ====
SPREADSHEET_NAME = "express-claim-app"
MAIN_SHEET = "Sheet1"
CREDENTIALS_FILE = "credentials.json"
# =================

# 初始化 Google Sheets 客户端
def get_gsheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    return client

# 路由主页
@app.route("/", methods=["GET", "POST"])
def index():
    message = None
    result = None

    if request.method == "POST":
        tracking = request.form.get("tracking", "").strip()
        nickname = request.form.get("nickname", "").strip()

        if tracking:
            client = get_gsheet()
            sheet = client.open(SPREADSHEET_NAME).worksheet(MAIN_SHEET)
            data = sheet.get_all_records()
            df = pd.DataFrame(data)

            if tracking in df["快递单号"].values:
                # 认领逻辑
                if nickname:
                    df.loc[df["快递单号"] == tracking, "谁的快递"] = nickname
                    sheet.clear()
                    sheet.update([df.columns.values.tolist()] + df.values.tolist())

                    # 更新个人子表
                    if nickname not in [ws.title for ws in client.open(SPREADSHEET_NAME).worksheets()]:
                        client.open(SPREADSHEET_NAME).add_worksheet(title=nickname, rows="100", cols="10")
                    user_ws = client.open(SPREADSHEET_NAME).worksheet(nickname)
                    user_df = df[df["谁的快递"] == nickname].copy()
                    user_ws.clear()
                    user_ws.update([user_df.columns.values.tolist()] + user_df.values.tolist())

                    message = f"快递 {tracking} 成功认领为「{nickname}」✅"
                else:
                    message = f"已查询到快递 {tracking}，但未填写昵称，未进行认领。"
                
                # 构造查询结果展示
                matched = df[df["快递单号"] == tracking].iloc[0]
                result = {
                    "快递单号": matched["快递单号"],
                    "重量（kg）": matched["重量（kg）"],
                    "谁的快递": matched.get("谁的快递", "")
                }
            else:
                message = f"未找到快递单号 {tracking} ❌"

    return render_template("index.html", message=message, result=result)

# ==== Render 指定端口 ====
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
