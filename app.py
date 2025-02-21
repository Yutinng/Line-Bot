import re
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.webhooks import (
    FollowEvent,
    MessageEvent,
    TextMessageContent,
    LocationMessageContent,
    PostbackEvent
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    ImageMessage
)
from linebot.v3.exceptions import InvalidSignatureError
from handlers import news                                             # 新聞
from handlers.wordcloud import fetch_google_news, generate_wordcloud  # 文字雲
from handlers.horoscope import get_horoscope_content                  # 星座
from handlers.earthquake import get_earthquake_info                   # 地震
from handlers.weather import get_weather_info                         # 天氣
from handlers.expense import save_expense, parse_expense_input, get_today_expense, get_monthly_expense       # 記帳功能
from config import ACCESS_TOKEN, CHANNEL_SECRET, line_bot_api, handler, configuration, CWA_TOKEN, user_state

app = Flask(__name__)


@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info(f"Received request body: {body}")  # Debug 用

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

# **加入好友時發送歡迎訊息**
@handler.add(FollowEvent)
def handler_follow(event):
    welcome_message = TextMessage(text="👋 歡迎加入！我是你的生活小助理。\n"
                                   "📰 查詢新聞: '新聞' 或 'news'\n"
                                   "🔮 查詢星座運勢: '今日星座運勢'\n"
                                   "🌦 查詢天氣: '天氣' 或傳送位置資訊\n"
                                   "🌍 查詢地震資訊: '地震'\n"
                                   "💰 記帳: 輸入『記帳』來開始記帳")
    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[welcome_message]
            )
        )

# **處理訊息事件**
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    msg = str(event.message.text).strip()
    reply_messages = []
    
    # **處理新聞查詢**
    if re.match(r"^(新聞|news)$", msg, re.IGNORECASE):
        reply_text = news.get_hot_news()
        google_news_titles = fetch_google_news(max_pages=3)  # 爬取 Google 新聞
        image_path = generate_wordcloud(google_news_titles)  # 生成新聞文字雲
        image_url = request.url_root + image_path  # 完整 URL
        image_url = image_url.replace("http", "https")  # LINE 只支援 https

        reply_messages.append(TextMessage(text=reply_text))
        reply_messages.append(ImageMessage(original_content_url=image_url, preview_image_url=image_url))

    # **處理星座運勢**
    elif msg == "今日星座運勢":
        user_state[user_id] = "awaiting_zodiac"
        reply_messages.append(TextMessage(text="🔎請輸入您要查詢的星座名稱（如：摩羯座、獅子座）"))

    elif user_id in user_state and user_state[user_id] == "awaiting_zodiac":
        user_zodiac = msg
        reply_text = get_horoscope_content(user_zodiac)

        if "⚠️ 找不到" in reply_text or "請檢查輸入的星座名稱" in reply_text:
            reply_messages.append(TextMessage(text=f"⚠️ 查無 {user_zodiac} 星座，請重新輸入正確的星座名稱（如：魔羯座、獅子座）"))
        else:
            del user_state[user_id]  # 正確輸入後移除狀態
            reply_messages.append(TextMessage(text=reply_text))

    # **處理地震查詢**
    elif msg == "地震":
        earthquake_info = get_earthquake_info(CWA_TOKEN)
        reply_messages.append(TextMessage(text=earthquake_info[0]))  # 地震文字資訊
        if earthquake_info[1]:  # 如果有圖片，則附上
            reply_messages.append(ImageMessage(original_content_url=earthquake_info[1], preview_image_url=earthquake_info[1]))

    # **處理天氣查詢**
    elif msg == "天氣":
        reply_messages.append(TextMessage(text="📍 請傳送您的 位置資訊，我會告訴你現在的天氣！ 🌦"))

    
    # **記帳功能：啟動記帳流程**
    if msg == "記帳":
        user_state[user_id] = "awaiting_expense"
        reply_messages.append(TextMessage(text="📝 請輸入您的支出項目與金額（例如：晚餐 120）"))

    elif user_id in user_state and user_state[user_id] == "awaiting_expense":
        sub_category, amount = parse_expense_input(msg)
        if sub_category and amount:
            user_state[user_id] = {
                "status": "awaiting_category",
                "sub_category": sub_category,
                "amount": amount
            }
            reply_messages.append(TextMessage(text="📌 請選擇此筆支出的分類（餐飲、交通、娛樂、購物、醫療、日常、其他）"))
        else:
            reply_messages.append(TextMessage(text="❌ 無法識別格式，請輸入類似『晚餐 120』"))

    elif user_id in user_state and isinstance(user_state[user_id], dict) and user_state[user_id].get("status") == "awaiting_category":
        category = msg.strip()
        if category not in ["餐飲", "交通", "娛樂", "購物", "醫療", "日常", "其他"]:
            reply_messages.append(TextMessage(text="❌ 無效的類別，請選擇：餐飲、交通、娛樂、購物、醫療、日常、其他"))
        else:
            sub_category = user_state[user_id]["sub_category"]
            amount = user_state[user_id]["amount"]
            save_expense(category, sub_category, amount, user_id)

            formatted_amount = int(amount) if amount.is_integer() else round(amount, 2)
            reply_messages.append(TextMessage(text=f"✅ 已記錄 {category}（{sub_category}）費用：{formatted_amount} 元"))

            del user_state[user_id]  # **記帳完成，刪除狀態**
    elif re.match(r"^(今天花了多少\？?|本月花了多少\？?)$", msg):
        if "今天" in msg:
            reply_text = get_today_expense(user_id)
        else:
            reply_text = get_monthly_expense(user_id)

        print(f"DEBUG: 查詢回應 - {reply_text}")  # ✅ Debug 訊息

        reply_messages.append(TextMessage(text=reply_text))

    
    # **統一回應所有訊息**
    if reply_messages:
        with ApiClient(configuration) as api_client:
            messaging_api = MessagingApi(api_client)
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=reply_messages
                )
            )


# **處理位置訊息（天氣）**
@handler.add(MessageEvent, message=LocationMessageContent)
def handle_location(event):
    address = event.message.address.replace("台", "臺")  # 「台」→「臺」
    weather_info = get_weather_info(address)  # 查詢天氣資訊

    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=weather_info)]
            )
        )

@handler.add(PostbackEvent)
def handle_postback(event):
    user_id = event.source.user_id
    data = event.postback.data
    
    reply_messages = []

    # 處理記帳類別選擇
    if data.startswith("category="):
        category = data.split("=")[1]
        user_state[user_id] = {"status": "waiting_for_amount", "category": category}
        reply_text = f"請輸入 {category} 的支出金額（例如：120）"
        reply_messages(event.reply_token, reply_text)

    # 處理金額輸入
    elif data.startswith("amount="):
        amount = float(data.split("=")[1])
        if user_id in user_state and user_state[user_id]["status"] == "waiting_for_amount":
            category = user_state[user_id]["category"]
            save_expense(category, "", amount, user_id)
            del user_state[user_id]
            reply_text = f"✅ 已記錄 {category} 費用：{int(amount) if amount.is_integer() else amount} 元"
            reply_messages(event.reply_token, reply_text)


if __name__ == "__main__":
    app.run(
        debug=True,    # 啟用除錯模式
        host="0.0.0.0", # 設定 0.0.0.0 會對外開放
        port=5000       # 啟用 port 號
    )
