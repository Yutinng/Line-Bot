import os
import google.generativeai as genai
import re
import json
from handlers.expense import save_expense, get_today_expense, get_weekly_expense, get_monthly_expense, get_monthly_income

# 設定 Gemini AI API 金鑰
GOOGLE_API_KEY1 = os.getenv('GOOGLE_API_KEY1')
genai.configure(api_key=GOOGLE_API_KEY1)

# 記帳類別
EXPENSE_CATEGORIES = ["餐飲", "交通", "娛樂", "購物", "醫療", "日常"]
INCOME_CATEGORIES = ["薪水", "獎金", "投資", "補助"]

# 清理 AI JSON 回應，避免解析錯誤
def clean_json_response(response):
    """移除可能的 Markdown 標記，確保 JSON 可解析"""
    response = response.strip()  # 去除頭尾空白
    response = re.sub(r"```json|```", "", response)  # 移除 ```json 和 ```
    return response

# 更新主函數：允許同時處理「記帳」與「查詢」
def process_user_input(user_id, input_text):
    """利用 AI 判斷使用者輸入的意圖，並執行對應的動作（記帳與查詢皆可同時執行）"""

    # **讓 AI 解析輸入，並回應 JSON 格式**
    prompt = f"""
    你是一個智慧財務助理，請幫助用戶解析記帳與查詢請求。
    
    ⚠️ **請特別注意**：
    1. **如果使用者的輸入為「星座」或「股票」相關內容，請回應 `null`，不要解析！**
       - **星座關鍵字**：「星座」「今日星座運勢」「運勢」「摩羯座」「獅子座」等。
       - **股票關鍵字**：「股票」「查詢股票」，或 **4~6 位數的純數字（如 2330、2412）**。

    2. **如果使用者是記帳**（例如：「午餐120」、「薪水50000」），請回應：
       {{"記帳": [{{"類型": "支出/收入", "類別": "<分類>", "金額": <金額>}}]}}
       可能的類別如下，若不在類別裡也可以自行判斷屬於哪個類別：
       - 支出類別：{", ".join(EXPENSE_CATEGORIES)}
       - 收入類別：{", ".join(INCOME_CATEGORIES)}
       
       例子：
       - "午餐120" → 類型: 支出, 類別: 餐飲
       - "薪水50000" → 類型: 收入, 類別: 薪水
       - "搭捷運30" → 類型: 支出, 類別: 交通
       - "投資收益2000" → 類型: 收入, 類別: 投資
       - "買衣服500"→ 類型: 支出, 類別: 購物
       - "唱歌100"→ 類型: 支出, 類別: 娛樂

    3. **如果使用者是查詢**（例如：「這週花多少？」、「我這個月收入多少？」），請回應：
       {{"查詢": [{{"查詢類型": "<今日支出/本週支出/本月支出/本月收入>"}}]}}

    4. **如果使用者同時輸入「記帳」與「查詢」**，請回應：
       {{"記帳": [...], "查詢": [...]}}

    5. **如果使用者詢問是否提供財務建議**（例如：「請給我建議」、「如何理財？」），請回應：
       {{"建議": true}}

    6. **如果使用者的輸入不符合以上規則，或 AI 不確定該如何分類，請回應 `null`，不要亂猜！**

    **請確保回應「純 JSON」，不包含任何額外的解釋或 Markdown（例如 ` ```json `）**
    
    **使用者輸入**：
    "{input_text}"
    """

    model = genai.GenerativeModel("gemini-1.5-pro")

    try:
        response = model.generate_content(prompt).text.strip()
        response = clean_json_response(response)  # **清理 AI JSON**
        result = json.loads(response)  # **解析 JSON**
        
        # ✅ **確保 result 不是 None**
        if result is None or not isinstance(result, dict):
            return "null"  # **如果 AI 沒有回應 JSON，則回傳 "null"**

    except json.JSONDecodeError as e:
        return f"⚠️ AI 解析 JSON 失敗：{str(e)}"

    output_messages = []  # 存放 AI 回應的結果
    records = None  # 確保 records 變數存在

    # **處理「記帳模式」**
    if "記帳" in result:
        for transaction in result["記帳"]:
            record_type = transaction["類型"]
            category = transaction["類別"]
            amount = transaction["金額"]

            # 確保金額是數字
            if not isinstance(amount, (int, float)):
                return "⚠️ 未偵測到金額，請確認輸入格式"

            # 儲存記帳資料
            save_result = save_expense(category, amount, user_id, record_type)
            output_messages.append(save_result)

    # **處理「查詢模式」**
    if "查詢" in result:
        for query in result["查詢"]:
            query_type = query["查詢類型"]

            if query_type == "今日支出":
                records = get_today_expense(user_id)
            elif query_type == "本週支出":
                records = get_weekly_expense(user_id)
            elif query_type == "本月支出":
                records = get_monthly_expense(user_id)
            elif query_type == "本月收入":
                records = get_monthly_income(user_id)
            else:
                output_messages.append("⚠️ AI 無法判斷查詢類型，請嘗試不同的說法")
                continue  # 跳過不支援的查詢
            
            output_messages.append(records)

    # **處理「使用者是否要求財務建議」**
    if result.get("建議") and records:
        advice = generate_financial_advice(records)
        output_messages.append(advice)

    return "\n\n".join(str(m) for m in output_messages if m)  # **確保結果不為 None**

# AI 生成財務建議
def generate_financial_advice(records):
    """利用 AI 根據查詢結果提供財務建議"""

    # **確保 records 轉換為字串**
    if isinstance(records, int):  
        records_str = f"💰 總收入: {records} 元"
    elif isinstance(records, list):
        records_str = "\n".join(records)
    elif isinstance(records, dict):
        records_str = "\n".join([f"{k}: {v} 元" for k, v in records.items()])
    else:
        records_str = str(records)

    prompt = f"""
    你是一位智慧財務顧問，以下是使用者的財務數據：
    {records_str}
    
    請提供一段財務建議，幫助使用者更有效管理財務。
    """

    model = genai.GenerativeModel("gemini-1.5-pro")
    response = model.generate_content(prompt).text.strip()
    
    return records_str + "\n\n💡 AI 理財建議：" + response

"""
# 測試
user_id = 12345
queries = [
    "我這個月花了多少"
]

for query in queries:
    response = process_user_input(user_id, query)
    print(f"🔹 使用者輸入: {query}")
    print(f"🟢 AI 回應: {response}\n")
"""