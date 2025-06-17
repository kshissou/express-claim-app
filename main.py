from flask import Flask, request, render_template
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os
import json
import tempfile
import sys

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
    print(f"📥 收到请求：{request.method}", file=sys.stderr)  # 🟢调试信息输出

    message = None
    result = None

    if request.method == "POST":
        tracking = request.form.get("tracking", "").strip()
        nickname = request.form.get("nickname", "").strip()

        print(f"🔎 提交内容 tracking={tracking}, nickname={nickname}", file=sys.stderr)

        if tracking:
            client = get_gsheet()
            sheet = client.open(SPREADSHEET_NAME).worksheet(MAIN_SHEET)
            data = sheet.get_all_records()
            df = pd.DataFrame(data)

            print("📄 表头：", df.columns.tolist(), file=sys.stderr)
            print("📄 当前数据：", df.to_dict(orient="records"), file=sys.stderr)

            if "快递单号" not in df.columns:
                message = "❌ 表格中找不到列「快递单号」，请检查表头"
                return render_template("index.html", message=message)

            if tracking in df["快递单号"].astype(str).values:
                if nickname:
                    df.loc[df["快递单号"].astype(str) == tracking, "谁的快递"] = nickname
                    sheet.clear()
                    sheet.update([df.columns.values.tolist()] + df.values.tolist())

                    # 更新子表
                    if nickname not in [ws.title for ws in client.open(SPREADSHEET_NAME).worksheets()]:
                        client.open(SPREADSHEET_NAME).add_worksheet(title=nickname, rows="100", cols="10")
                    user_ws = client.open(SPREADSHEET_NAME).worksheet(nickname)
                    user_df = df[df["谁的快递"] == nickname].copy()
                    user_ws.clear()
                    user_ws.update([user_df.columns.values.tolist()] + user_df.values.tolist())

                    message = f"✅ 快递 {tracking} 成功认领为「{nickname}」"
                else:
                    message = f"ℹ️ 查询到快递 {tracking}，但未填写昵称，未认领"

                matched = df[df["快递单号"].astype(str) == tracking].iloc[0]
                result = {
                    "快递单号": matched["快递单号"],
                    "重量（kg）": matched.get("重量（kg）", ""),
                    "谁的快递": matched.get("谁的快递", "")
                }
            else:
                message = f"❌ 未找到快递单号 {tracking}"

    return render_template("index.html", message=message, result=result)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
