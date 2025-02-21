import re
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.webhooks import (
    FollowEvent,
    MessageEvent,
    TextMessageContent,
    LocationMessageContent
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
from handlers import news
from handlers.wordcloud import fetch_google_news, generate_wordcloud 
from handlers.horoscope import get_horoscope_content
from handlers.earthquake import get_earthquake_info
from handlers.weather import get_weather_info 

from config import ACCESS_TOKEN, CHANNEL_SECRET, line_bot_api,handler,configuration,CWA_TOKEN


app = Flask(__name__)

# 用戶狀態管理
user_state = {}


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header valu
    signature = request.headers['X-Line-Signature']
        
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info(f"Received request body: {body}")  # debug 用

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

# 加入好友==================================================================================================加入好友
@handler.add(FollowEvent)
def handler_follow(event):
    # 傳送歡迎訊息
    welcome_message  = TextMessage(text="👋 歡迎加入！我是你的生活小助理。\n"
                                   "📰 查詢目前熱搜新聞請輸入: '新聞' 或 'news'\n"
                                   "🔮 查詢星座運勢請輸入: '今日星座運勢'\n"
                                   "🌦 查詢天氣請輸入: '天氣' 或直接傳送位置資訊\n"
                                   "🌍 查詢最新發生地震資訊請輸入: '地震'\n"
                                )
    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[welcome_message]
            )
        )

# 處理訊息==================================================================================================處理訊息
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id  

    # 先將使用者的輸入轉換成大寫並去除空白(strip)，存到變數 msg
    msg = str(event.message.text).upper().strip()      # event.message.text:使用者傳入的訊息
    
    with ApiClient(configuration) as api_client:       # 建立 API 客戶端連線
        line_bot_api = MessagingApi(api_client)        # 初始化 Messaging API

    # =====================================================================================
        # 使用者輸入 "新聞" 或 "news" 或 "NEWS"，抓取熱搜前10新聞並返回文字雲
        if re.match(r"^(新聞|news)$", msg, re.IGNORECASE):       # 不分大小寫
            reply_text = news.get_hot_news()                     # 回覆訊息的為 執行 news.get_hot_news 結果
            
            google_news_titles = fetch_google_news(max_pages=3)  # 爬取 Google 新聞
            image_path = generate_wordcloud(google_news_titles)  # 生成新聞文字雲
            image_url = request.url_root + image_path            # 完整 URL
            image_url = image_url.replace("http", "https")       # LINE 無法讀取http,改為https
            
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(text=reply_text),
                        ImageMessage(original_content_url=image_url, preview_image_url=image_url)
                    ]
                )
            )
        # 使用者輸入 "今日星座運勢"，抓取相對應星座運勢
        if msg == "今日星座運勢":
            user_state[user_id] = "awaiting_zodiac"  # 記錄該用戶正在查詢星座
            reply_text = "🔎請輸入您要查詢的星座名稱（如：魔羯座、獅子座）"
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text)]
                )
            )
            return
        if user_id in user_state and user_state[user_id] == "awaiting_zodiac":
            user_zodiac = msg  
            reply_text = get_horoscope_content(user_zodiac) 

            # 如果查無此星座，請使用者重新輸入，直到輸出運勢結果為止
            if "⚠️ 找不到" in reply_text or "請檢查輸入的星座名稱" in reply_text:
                reply_text = f"⚠️ 查無 {user_zodiac} 星座，請重新輸入正確的星座名稱（如：魔羯座、獅子座）"
            else:
                del user_state[user_id]  # 輸入正確後，結束查詢狀態

            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text)]
                )
            )
            return
        
        # 使用者輸入 "地震"，返回最新地震資訊
        elif msg == "地震":
            earthquake_info = get_earthquake_info(CWA_TOKEN)  # 取得地震資訊
            reply_text = earthquake_info[0]                   # 文字
            image_url = earthquake_info[1]                    # 圖片

            messages = [TextMessage(text=reply_text)]  
            if image_url:  
                messages.append(ImageMessage(original_content_url=image_url, preview_image_url=image_url))
            with ApiClient(configuration) as api_client:
                messaging_api = MessagingApi(api_client)  
                messaging_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=messages  
                    )
                )
        
        # 使用者輸入 "天氣"，提示他傳送位置資訊
        elif msg == "天氣":
            reply_text = "📍 請傳送您的 位置資訊，我會幫您查詢當地天氣！ 🌦"
            try:
                with ApiClient(configuration) as api_client:
                    messaging_api = MessagingApi(api_client)
                    messaging_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[TextMessage(text=reply_text)]
                        )
                    )
            except Exception as e:
                print(f"An error occurred: {e}")


# 處理位置訊息================================================================================================處理位置訊息
@handler.add(MessageEvent, message=LocationMessageContent)
def handle_location(event):
    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)

        # 取得地址
        address = event.message.address.replace("台", "臺")  # 確保「台」→「臺」
        weather_info = get_weather_info(address)  # 查詢天氣資訊

        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=weather_info)]
            )
        )

            

if __name__ == "__main__":
    app.run(
        debug=True,    # 啟用除錯模式
        host="0.0.0.0", # 設定 0.0.0.0 會對外開放
        port=5000       # 啟用 port 號
    )
