from flask import Flask, render_template, request, redirect
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# ---------------- 配置 ----------------
SPREADSHEET_NAME = "快递包裹自动同步"
MAIN_SHEET = "Sheet1"
CREDENTIALS_FILE = "credentials.json"
# ------------------------------------

app = Flask(__name__)

def get_gsheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scope)
    client = gspread.authorize(creds)
    return client

@app.route("/", methods=["GET", "POST"])
def index():
    message = None
    result = None

    if request.method == "POST":
        tracking = request.form.get("tracking").strip()
        name = request.form.get("name", "").strip()

        if not tracking:
            message = "请输入快递单号。"
        else:
            client = get_gsheet()
            sheet = client.open(SPREADSHEET_NAME).worksheet(MAIN_SHEET)
            data = sheet.get_all_records()

            found = False
            for i, row in enumerate(data):
                if row["快递单号"] == tracking:
                    result = row
                    found = True

                    # 如果填写了认领人，更新主表
                    if name:
                        sheet.update_cell(i + 2, 3, name)  # 第3列是“谁的快递”
                        update_user_sheet(client, name, tracking, row["重量（kg）"])
                        message = f"🎉 认领成功！{tracking} 现在归 {name} 所有"

            if not found:
                message = "未找到该快递单号。"

    return render_template("index.html", result=result, message=message)

def update_user_sheet(client, username, tracking, weight):
    try:
        sheet = client.open(SPREADSHEET_NAME)
        if username not in [ws.title for ws in sheet.worksheets()]:
            sheet.add_worksheet(title=username, rows="100", cols="3")
        ws = sheet.worksheet(username)
        existing = ws.get_all_records()

        # 移除已有条目（更新而非重复）
        new_data = [row for row in existing if row["快递单号"] != tracking]
        new_data.append({"快递单号": tracking, "重量（kg）": weight})

        df = pd.DataFrame(new_data)
        total = df["重量（kg）"].astype(float).sum()
        df.loc[len(df.index)] = ["总计", total]

        ws.clear()
        ws.update([df.columns.values.tolist()] + df.values.tolist())
    except Exception as e:
        print("更新用户工作表出错：", e)

if __name__ == "__main__":
    app.run(debug=True)
