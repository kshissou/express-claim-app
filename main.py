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
    json_str = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
        tmp.write(json_str)
        tmp.flush()
        creds = Credentials.from_service_account_file(tmp.name, scopes=scopes)
    client = gspread.authorize(creds)
    return client

@app.route("/", methods=["GET", "POST"])
def index():
    message_list = []
    result_list = []
    input_tracking = ""
    nickname = ""

    if request.method == "POST":
        input_tracking = request.form.get("tracking", "").strip()
        nickname = request.form.get("nickname", "").strip()
        client = get_gsheet()
        sheet = client.open(SPREADSHEET_NAME).worksheet(MAIN_SHEET)
        data = sheet.get_all_records()
        df = pd.DataFrame(data)

        # 分割单号（空格、换行、逗号、顿号等）
        tracking_list = [s.strip() for s in 
                         input_tracking.replace("\n", " ")
                                       .replace("，", " ")
                                       .replace(",", " ")
                                       .replace("、", " ")
                                       .replace("　", " ")  # 全角空格
                                       .split(" ")
                         if s.strip()]

        for tracking in tracking_list:
            if tracking in df["快递单号"].astype(str).values:
                row = df[df["快递单号"].astype(str) == tracking].iloc[0]
                current_owner = row["谁的快递"]

                if nickname:  # 用户填了昵称，要认领
                    df.loc[df["快递单号"].astype(str) == tracking, "谁的快递"] = nickname
                    message_list.append(f"快递 {tracking} 成功认领为「{nickname}」✅")
                else:  # 没填昵称，只查询
                    if current_owner:
                        message_list.append(f"快递 {tracking} 已被认领为「{current_owner}」✅")
                    else:
                        message_list.append(f"已查询到快递 {tracking}，但未填写昵称，未进行认领。")

                result_list.append({
                    "快递单号": tracking,
                    "重量（kg）": row["重量（kg）"],
                    "谁的快递": nickname or current_owner or ""
                })
            else:
                message_list.append(f"未找到快递单号 {tracking} ❌")

        # 更新主表和子表（仅当有认领）
        if nickname and any(df["谁的快递"] == nickname):
            sheet.clear()
            sheet.update([df.columns.values.tolist()] + df.values.tolist())
            ws_list = [ws.title for ws in client.open(SPREADSHEET_NAME).worksheets()]
            if nickname not in ws_list:
                client.open(SPREADSHEET_NAME).add_worksheet(title=nickname, rows="100", cols="10")
            user_ws = client.open(SPREADSHEET_NAME).worksheet(nickname)
            user_df = df[df["谁的快递"] == nickname].copy()
            user_ws.clear()
            user_ws.update([user_df.columns.values.tolist()] + user_df.values.tolist())

    return render_template("index.html",
                           message="\n".join(message_list),
                           result=result_list,
                           input_tracking=input_tracking,
                           nickname=nickname)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
