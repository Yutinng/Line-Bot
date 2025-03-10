"""
記帳功能
當用戶輸入"中文 + 數字"格式,利用正則表達式判斷msg,開始記帳功能
目前功能：查詢今日支出、查詢本周支出、查詢本月支出、查詢本月收入、設定預算及預算提醒

優化日誌：
1. 當已記錄該筆帳務,回傳帳務資訊不包含小數點
2. 加入 ConfirmTemplate, 讓用戶點選收入或支出
3. 簡化函數
"""
import os
from mysql.connector import pooling, Error
from datetime import datetime, timedelta
import logging
from get_username import get_line_username

# 主要類別
CATEGORIES = ["餐飲", "交通", "娛樂", "購物", "醫療", "日常", "其他"]
INCOME_CATEGORIES = ["薪水", "獎金", "投資", "其他"]
BUDGET_PERIODS = ["週預算", "月預算"]


# 建立 MySQL 連線池
pool = pooling.MySQLConnectionPool(
    host=os.getenv('MYSQL_HOST'),  
    port=os.getenv('MYSQL_PORT'),  
    user=os.getenv('MYSQL_USER'),
    password=os.getenv('MYSQL_PASSWORD'),
    database=os.getenv('MYSQL_DATABASE')
)

def get_db_connection():
    """取得 MySQL 連線"""
    return pool.get_connection()

# 儲存帳務訊息
def save_expense(category, amount, user_id, record_type):
    """儲存收入或支出記錄"""
    try:
        amount = int(float(amount))  
        user_name = get_line_username(user_id)
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO expenses (category, amount, user_id, user_name, type, date) VALUES (%s, %s, %s, %s, %s, NOW())",
                (category, amount, user_id, user_name, record_type)
            )
            conn.commit()
            return f"✅ 已記錄：{record_type} - {category} {amount} 元"
    except Error as e:
        logging.error(f"Database error in save_expense: {e}")
        return "⚠️ 記帳失敗，請稍後再試"

# 通用查詢函數
def fetch_financial_records(user_id, period, record_type):
    """查詢指定時間範圍的財務記錄，並回傳總支出"""
    now = datetime.now()
    conditions = {
        'today': ("DATE(date) = %s", [now.strftime("%Y-%m-%d")]),
        'week': ("DATE(date) >= %s", [(now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")]),
        'month': ("YEAR(date) = %s AND MONTH(date) = %s", [now.year, now.month])
    }
    condition = conditions.get(period)
    if not condition:
        return None, "⚠️ 不支援的時間範圍"

    query = f"""
        SELECT category, SUM(amount) as total
        FROM expenses
        WHERE {condition[0]} 
          AND user_id = %s 
          AND type = %s
        GROUP BY category
    """
    params = condition[1] + [user_id, record_type]

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            records = cursor.fetchall()

            # ✅ 取得該時段的總支出，並確保轉換為 int
            cursor.execute(f"""
                SELECT SUM(amount) FROM expenses
                WHERE {condition[0]} 
                  AND user_id = %s 
                  AND type = %s
            """, params)
            total_expense = cursor.fetchone()[0]
            total_expense = int(total_expense) if total_expense else 0  # **確保是 int**
            
            return records, total_expense  # ✅ 回傳「各類支出」+「總支出」
    except Error as e:
        logging.error(f"Database error in fetch_financial_records: {e}")
        return None, "⚠️ 查詢失敗，請稍後重試"


# 格式化回應
def format_response(result, period, record_type, user_id, total_expense):
    """格式化查詢結果，並附加預算提醒（但今日支出不顯示預算）"""
    if not isinstance(result, list):
        return "⚠️ 資料庫查詢異常"

    period_titles = {'today': '今日', 'week': '本週', 'month': '本月'}
    emoji = '🔹' if record_type == '支出' else '💰'
    type_text = '支出' if record_type == '支出' else '收入'

    if not result:
        return f"📅 {period_titles.get(period, '')} 還沒有任何{type_text}記錄"

    response = f"📅 {period_titles[period]} 各類{type_text}：\n"
    total_sum = 0

    for category, total in result:
        total = int(total)  # ✅ 確保是 int
        response += f"{emoji} {category}: {total:,} 元\n"  # ✅ 加上千分位
        total_sum += total

    response += f"\n💵 {type_text}總計：{total_sum:,} 元"  # ✅ 確保總計也加上千分位

    # ✅ 查詢「今日支出」時不顯示預算提醒
    if record_type == '支出' and period != 'today':
        response = add_budget_alerts(response, user_id, period, total_expense)

    return response


# 查詢支出 / 收入
def get_today_expense(user_id):
    result, total_expense = fetch_financial_records(user_id, 'today', '支出')
    return format_response(result, 'today', '支出', user_id, total_expense)

def get_weekly_expense(user_id):
    records, total_expense = fetch_financial_records(user_id, 'week', '支出')
    return format_response(records, 'week', '支出', user_id, total_expense)  

def get_monthly_expense(user_id):
    result, total_expense = fetch_financial_records(user_id, 'month', '支出')
    return format_response(result, 'month', '支出', user_id, total_expense)

def get_monthly_income(user_id):
    result, total_income = fetch_financial_records(user_id, 'month', '收入')
    if not result:  # 如果沒有任何收入紀錄
        return "📅 本月尚未取得收入"
    return format_response(result, 'month', '收入', user_id, total_income)

#=====================================================================================================預算
#=====================================================================================================預算

# 設定預算
def set_budget(user_id, amount, period):
    """設定或更新使用者的總預算（每月 / 每週）"""
    if period not in ["monthly", "weekly"]:
        return "⚠️ 週期格式錯誤，僅支援 monthly/weekly"
    if not str(amount).isdigit():
        return "⚠️ 金額需為整數"

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # ✅ 先查詢當前是否已設定過預算
            cursor.execute("SELECT amount FROM budgets WHERE user_id = %s AND period = %s", (user_id, period))
            existing_budget = cursor.fetchone()

            if existing_budget:
                old_amount = existing_budget[0]
                if int(amount) == old_amount:
                    return f"⚠️ 你的 {period} 預算已經是 {amount} 元，無需更新！"
                
                # ✅ 更新現有預算
                cursor.execute(
                    "UPDATE budgets SET amount = %s WHERE user_id = %s AND period = %s",
                    (amount, user_id, period)
                )
                conn.commit()
                return f"🔄 已更新 {period} 預算為 {amount} 元（原本：{old_amount} 元）"
            
            # ✅ 如果沒有舊預算，則插入新預算
            cursor.execute(
                "INSERT INTO budgets (user_id, amount, period) VALUES (%s, %s, %s)",
                (user_id, int(amount), period)
            )
            conn.commit()
            return f"✅ 已設定 {period} 預算為 {amount} 元"

    except Error as e:
        logging.error(f"Database error in set_budget: {e}")
        return "⚠️ 設定失敗，請檢查格式"


# 預算查詢
def get_budgets(user_id, period=None):
    """取得用戶的總預算（可選擇 monthly 或 weekly）"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT amount, period FROM budgets WHERE user_id = %s"
            params = [user_id]
            if period:
                query += " AND period = %s"
                params.append(period)
            cursor.execute(query, params)
            return cursor.fetchall()
    except Error as e:
        logging.error(f"Database error in get_budgets: {e}")
        return None

# 預算提醒
def add_budget_alerts(response, user_id, period, total_expense):
    """在查詢結果中追加預算提醒"""
    budget_period = '本月' if period == 'month' else '本週'  
    budgets = get_budgets(user_id, 'monthly' if period == 'month' else 'weekly')

    if not budgets:
        return response  # ✅ 沒有設定預算，直接返回

    total_budget = budgets[0][0]  # 獲取預算金額
    percentage_used = int((total_expense / total_budget) * 100) if total_budget else 0  # ✅ 轉整數
    alerts = [f"📊 {budget_period}已使用 {total_expense:,}/{total_budget:,} 元（{percentage_used}%）"]  # ✅ 加千分位 & 無小數點

    # ✅ 超過 80% 提醒
    if total_expense >= total_budget * 0.8 and total_expense < total_budget:
        alerts.append(f"⚠️ {budget_period}支出已達 80% 預算，省著點！")

    # ✅ 超過 100% 提醒
    elif total_expense >= total_budget:
        alerts.append(f"🚨 {budget_period}支出已超過預算！吃土吧！")

    response += "\n——————————————\n🔔 預算提醒：\n" + "\n".join(alerts)
    return response
