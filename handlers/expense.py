import mysql.connector
import re
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from decimal import Decimal  
from linebot.v3.messaging import ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from config import user_state, MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE, configuration



# 主要支出類別
CATEGORIES = ["餐飲", "交通", "娛樂", "購物", "醫療", "日常", "其他"]

# 建立 MySQL 連線
def get_db_connection():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
    )

# 儲存記帳資料
def save_expense(category, sub_category, amount, user_id, record_type="支出"):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO expenses (category, sub_category, amount, user_id, type) VALUES (%s, %s, %s, %s, %s)",
        (category, sub_category, amount, user_id, record_type)
    )
    connection.commit()
    cursor.close()
    connection.close()

# 解析記帳輸入（獲取細分類和金額）
def parse_expense_input(text):
    match = re.match(r"(\D+)\s*(\d+)", text)
    if match:
        sub_category = match.group(1).strip()  # 例如 "早餐"
        amount = float(match.group(2))
        return sub_category, amount
    return None, None

# 查詢今日支出（顯示細分類）
def get_today_expense(user_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
        SELECT category, sub_category, SUM(amount) as total
        FROM expenses
        WHERE DATE(date) = %s AND user_id = %s
        GROUP BY category, sub_category
    """, (today, user_id))

    result = cursor.fetchall()
    cursor.close()
    connection.close()

    if result:
        response = "📅 今天各類支出：\n"
        for row in result:
            category, sub_category, total = row
            total = float(total)  # ✅ 轉換 Decimal 為 float
            formatted_total = int(total) if total.is_integer() else round(total, 2)
            response += f"🔹 {category} - {sub_category}: {formatted_total} 元\n"
    else:
        response = "📅 今天還沒有任何支出記錄"

    return response

# 查詢本月支出（顯示細分類）
def get_monthly_expense(user_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    now = datetime.now()
    year, month = now.year, now.month  # 取得當前年份與月份

    cursor.execute("""
        SELECT category, SUM(amount) as total
        FROM expenses
        WHERE YEAR(date) = %s AND MONTH(date) = %s AND user_id = %s
        GROUP BY category
    """, (year, month, user_id))

    result = cursor.fetchall()
    cursor.close()
    connection.close()

    if result:
        response = "📆 本月各類支出：\n"
        for row in result:
            category, total = row
            total_amount = int(total) if total % 1 == 0 else round(total, 2)
            response += f"🔹 {category}: {total_amount} 元\n"
    else:
        response = "📆 本月還沒有任何支出記錄"

    return response

# 處理 LINE 訊息（記帳）
def handle_expense_message(event, text):
    user_id = event.source.user_id

    # **步驟 1：如果使用者正在選擇類別**
    if user_id in user_state and user_state[user_id]["status"] == "waiting_for_category":
        category = text.strip()
        if category not in CATEGORIES:
            reply_text = "❌ 無效的類別，請選擇：餐飲、交通、娛樂、購物、醫療、日常、其他"
        else:
            # 取得 `sub_category` 和 `amount`
            sub_category = user_state[user_id]["sub_category"]
            amount = user_state[user_id]["amount"]

            # **步驟 2：儲存到 MySQL**
            save_expense(category, sub_category, amount, user_id)
            
            # ✅ 修正金額格式（去掉不必要的小數點）
            formatted_amount = int(amount) if amount.is_integer() else round(amount, 2)

            reply_text = f"✅ 已記錄 {category}（{sub_category}）費用：{formatted_amount} 元"

            # **清除使用者狀態**
            del user_state[user_id]

    elif text in ["今天花了多少", "本月花了多少"]:
        if text == "今天花了多少":
            reply_text = get_today_expense(user_id)
        else:
            reply_text = get_monthly_expense(user_id)

    else:
        # **步驟 3：解析使用者輸入的支出細分類和金額**
        sub_category, amount = parse_expense_input(text)
        if sub_category and amount:
            # **步驟 4：讓使用者選擇主要類別**
            user_state[user_id] = {
                "status": "waiting_for_category",
                "sub_category": sub_category,
                "amount": amount
            }
            reply_text = "📌 請選擇此筆支出的分類（餐飲、交通、娛樂、購物、醫療、日常、其他）"

        else:
            return False  # ✅ 修正這裡，讓 `app.py` 可以繼續處理其他功能

    # **回覆 LINE 使用者**
    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

    return True  # ✅ 記帳成功
