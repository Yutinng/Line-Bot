import re
import os
import cv2
import requests
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.webhooks import (
    FollowEvent,
    MessageEvent,
    TextMessageContent,
    LocationMessageContent,
    PostbackEvent,
    ImageMessageContent
)
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    ImageMessage,
    TextMessage,
    TemplateMessage,
    ConfirmTemplate,
    PostbackAction,
)
from linebot.v3.exceptions import InvalidSignatureError
from get_username import get_line_username
from handlers import news                                             # 新聞
from handlers.news_wordcloud import fetch_google_news, generate_wordcloud  # 文字雲
from handlers.horoscope import get_horoscope_content                  # 星座
from handlers.earthquake import get_earthquake_info                   # 地震
from handlers.weather import get_weather_info                         # 天氣
from handlers.expense import (save_expense, get_today_expense,        # 記帳功能
                              get_weekly_expense, get_monthly_expense,
                              get_monthly_income, set_budget
                            )  
from handlers.image_utils import clear_old_images    
from handlers.image_filters import (sketch_effect, emboss_effect, oilPaint_effect,
                                    blackWhite_effect, softGlow_effect, bigEyes_effect
                                )                                    # 圖片風格轉換功能
from handlers.stock_prediction import predict_stock_price, get_stock_name,get_technical_indicators
from handlers.stock_news import get_stock_news
from handlers.stock_kchart import plot_stock_chart
from handlers.stock_trend_chart import plot_stock_trend
from handlers.stock_watchlist import get_watchlist
from handlers.stock_watchlist import add_watchlist, remove_watchlist, get_watchlist
from quick_reply import expense_quickReply, stock_quickReply, image_quickReply
from handlers.breed_classifier import predict_breed  
from handlers.chat import chat_with_bard 
import ai_expense


app = Flask(__name__)


configuration = Configuration(access_token=os.getenv('ACCESS_TOKEN'))
line_handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))
api_client = ApiClient(configuration)  
line_bot_api = MessagingApi(api_client) 
CWA_TOKEN = os.getenv('CWA_TOKEN')
user_state = {}


@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info(f"Received request body: {body}")  # Debug 

    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

# 加入好友時發送歡迎訊息
@line_handler.add(FollowEvent)
def handler_follow(event):
    user_id = event.source.user_id  # 取得使用者 ID
    user_name = get_line_username(user_id)  
    
    # 歡迎訊息
    welcome_message = TextMessage(text=(
        f"👋 嗨！{user_name}，歡迎加入，我是你的生活小助理！\n"
        "——————————————\n"
        "📢 這裡有一些實用的功能：\n"
        "📰 即時新聞：輸入「新聞」或「news」查詢最新時事\n"
        "🔮 星座運勢：輸入「星座」或「今日星座運勢」查看你的運勢\n"
        "🌍 地震資訊：輸入「地震」查看最新地震消息\n"
        "🌦 天氣查詢：傳送你的 位置資訊 查看目前天氣狀況\n"
        "💰 記帳助手：輸入「類別 金額」，例如「餐飲 120」來開始記帳\n"
        "📈 股票分析：輸入股票代碼（如 2330）獲取預測股價、技術指標、K 線圖\n"
        "🖼 圖片風格轉換：傳送圖片，選擇想要的風格進行轉換\n"
        "🐶🐱 AI 影像辨識：傳送寵物圖片，辨識貓狗品種\n"
        "✨ 你也可以點擊下方 📌 查看更多功能 快速使用各項功能！"
    ))

    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[welcome_message]
        )
    )

#=================================================================================================訊息事件
#=================================================================================================訊息事件

# 處理訊息事件
@line_handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    msg = str(event.message.text).strip()
    reply_messages = []
    
    # 直接讓 AI 分析（AI 會自己回應null避免誤判）
    ai_expense_response = ai_expense.process_user_input(user_id, msg)
    print(f"🛠 記帳 AI 回應: {ai_expense_response}")  # Debug 訊息

    if ai_expense_response and ai_expense_response.strip() and ai_expense_response != "null":
        reply_messages.append(TextMessage(text=ai_expense_response))
    else:
        # 新聞
        if re.match(r"^(新聞|news)$", msg, re.IGNORECASE):
            reply_text = news.get_hot_news()
            google_news_titles = fetch_google_news(max_pages=3)           # 爬取 Google 新聞
            image_path = generate_wordcloud(google_news_titles)           # 生成新聞文字雲
            image_url = request.url_root + image_path                     # 完整 URL
            image_url = image_url.replace("http", "https")                # LINE只支援https

            reply_messages.append(TextMessage(text=reply_text))
            reply_messages.append(ImageMessage(original_content_url=image_url, preview_image_url=image_url))

        # 星座運勢
        elif re.match(r"^(今日星座運勢|星座|運勢)$", msg):
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

        # 地震
        elif msg == "地震":
            earthquake_info = get_earthquake_info(CWA_TOKEN)
            reply_messages.append(TextMessage(text=earthquake_info[0]))  # 地震文字資訊
            if earthquake_info[1]:  # 如果有圖片，則附上
                reply_messages.append(ImageMessage(original_content_url=earthquake_info[1], preview_image_url=earthquake_info[1]))

        # 天氣->好像有點多餘
        #elif msg == "天氣":
        #   reply_messages.append(TextMessage(text="📍 請傳送您的 位置資訊，我會告訴你現在的天氣！ 🌦"))

        # 記帳功能：配對「類別 + 金額」
        elif re.match(r"([\u4e00-\u9fa5]+)\s*(\d+)", msg): 
            match = re.match(r"([\u4e00-\u9fa5]+)\s*(\d+)", msg)
            category = match.group(1)  # 記錄類別
            amount = match.group(2)    # 記錄金額

            confirm_template = ConfirmTemplate(
                text=f"📌 請選擇這筆交易的類型\n\n類別：{category}\n金額：{amount} 元",
                actions=[
                    PostbackAction(
                        label="💰 收入",
                        data=f"記帳,收入,{category},{amount}",
                        display_text="收入"
                    ),
                    PostbackAction(
                        label="💸 支出",
                        data=f"記帳,支出,{category},{amount}",
                        display_text="支出"
                    )
                ]
            )
            template_message = TemplateMessage(
                alt_text="請選擇這筆交易的類型",
                template=confirm_template
            )
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[template_message]
                )
            )

        elif user_id in user_state and user_state[user_id].startswith("awaiting_budget"):
            period = "monthly" if "monthly" in user_state[user_id] else "weekly"

            if msg.isdigit():
                response_text = set_budget(user_id, int(msg), period)
                reply_messages.append(TextMessage(text=response_text))
                del user_state[user_id]  # 清除狀態
            else:
                reply_messages.append(TextMessage(text="⚠️ 請輸入有效的數字金額！"))

        # 查詢「今天 / 本週 / 本月支出、本月收入」
        elif msg in ["查詢今日支出", "查詢本週支出", "查詢本月支出", "查詢本月收入"]:
            if msg == "查詢今日支出":
                reply_text = get_today_expense(user_id)
            elif msg == "查詢本週支出":
                reply_text = get_weekly_expense(user_id)
            elif msg == "查詢本月支出":
                reply_text = get_monthly_expense(user_id)
            elif msg == "查詢本月收入":
                reply_text = get_monthly_income(user_id)

            if not reply_text:
                reply_text = "❌ 查詢失敗，請稍後再試"
            
            # QuickReply 選單顯示給用戶
            reply_messages.append(TextMessage(text=reply_text, quick_reply=expense_quickReply()))
            
        # 股票預測功能（偵測 數字，即股票代碼）
        elif re.match(r"^\d{4,6}(,\d{4,6})*$", msg):  # 允許 4～6 位數的股票查詢
            stock_codes = msg.split(',')
            reply_messages = []  # 儲存所有要回應的訊息
            success_results = []  # 成功的查詢結果
            error_results = []  # 失敗的查詢結果

            for stock_code in stock_codes:
                try:
                    stock_name = get_stock_name(stock_code)  # 取得中文股票名稱
                    tech_data = get_technical_indicators(stock_code)  # 取得技術指標
                    predicted_price = predict_stock_price(stock_code)  # 預測股價

                    if "error" in tech_data:
                        error_results.append(f"⚠️ {stock_code} 查詢失敗：{tech_data['error']}")
                        continue

                    # 組合技術指標
                    stock_result = f"🔹 {stock_code} {stock_name}\n"
                    stock_result += f"📌 最新股價：{tech_data['latest_price']} 元\n"
                    stock_result += f"📈 預測股價：{predicted_price:.2f} 元\n"
                    stock_result += f"——————————————\n"

                    # 技術指標訊號
                    stock_result += f"{tech_data['signals']}\n"

                    # 添加Quick Reply
                    quick_reply = stock_quickReply(stock_code, stock_name)
                    success_results.append(TextMessage(text=stock_result, quick_reply=quick_reply))

                except Exception as e:
                    error_results.append(f"⚠️ {stock_code} 查詢失敗，請輸入正確股票代碼")

            # 確保回應
            if success_results:
                reply_messages.extend(success_results)  # 讓多支股票的結果分開顯示
            if error_results:
                reply_messages.append(TextMessage(text="\n".join(error_results)))  # 顯示查詢失敗的訊息

            # 發送訊息
            if reply_messages:
                line_bot_api.reply_message(
                    ReplyMessageRequest(reply_token=event.reply_token, messages=reply_messages)
                )
        # 查詢股票清單
        elif msg == "查詢我的股票":
            user_id = event.source.user_id
            response = get_watchlist(user_id)
            reply_messages = []
            reply_messages.append(TextMessage(text=response))

        # 如果沒有匹配到任何已知指令，則使用Gemini
        else:
            bard_reply = chat_with_bard(msg)                    # 呼叫 Google Bard
            reply_messages.append(TextMessage(text=bard_reply))
                    
    # 統一回應所有訊息
    if reply_messages:
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=reply_messages
            )
        )

#=================================================================================================圖片處理
#=================================================================================================圖片處理
@line_handler.add(MessageEvent, message=ImageMessageContent)
def handle_image(event):
    user_id = event.source.user_id
    image_id = event.message.id
    image_path = f"static/transformed_images/{image_id}.jpg"

    # 舊圖片在下載新圖片前被刪除
    clear_old_images()  
    
    try:
        # 使用 requests 下載圖片
        url = f"https://api-data.line.me/v2/bot/message/{image_id}/content"
        headers = {"Authorization": f"Bearer {os.getenv('ACCESS_TOKEN')}"}
        
        response = requests.get(url, headers=headers, stream=True)

        if response.status_code == 200:
            with open(image_path, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print("✅ 圖片下載成功！")
        else:
            print(f"❌ 下載失敗: {response.status_code}, {response.text}")
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="❌ 圖片下載失敗，請再試一次！")]
                )
            )
            return

        # 利用 Quick Reply 讓用戶選擇風格
        quick_reply = image_quickReply(image_path)

        reply_message = TextMessage(
            text="請選擇要套用的風格 或 進行🐱🐶品種辨識",
            quick_reply=quick_reply
        )

        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[reply_message]
            )
        )

    except Exception as e:
        print(f"❌ 下載圖片失敗: {e}")  
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="❌ 圖片處理失敗，請再試一次！")]
            )
        )

#=================================================================================================位置事件
#=================================================================================================位置事件

# 位置訊息（天氣）
@line_handler.add(MessageEvent, message=LocationMessageContent)
def handle_location(event):
    user_id = event.source.user_id

    address = event.message.address.replace("台", "臺")  # 「台」→「臺」
    weather_info = get_weather_info(address)             # 查詢天氣資訊
    
    # degug:透過rich menu點擊後傳送位置資訊無法取得空氣品質
    if address:
        weather_info = get_weather_info(address)  # 查詢天氣資訊
        reply_messages = [TextMessage(text=weather_info)]
    else:
        reply_messages = [TextMessage(text="❌ 無法獲取您的位置資訊，請再試一次")]
    
    if user_id in user_state and user_state[user_id] == "awaiting_location":
        del user_state[user_id]

    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=weather_info)]
        )
    )

#=================================================================================================Postback事件
#=================================================================================================Postback事件

@line_handler.add(PostbackEvent)
def handle_postback(event):
    postback_data = event.postback.data  
    user_id = event.source.user_id
    reply_messages = []
    
    if postback_data == "查詢目前熱搜新聞":
        reply_text = news.get_hot_news()
        google_news_titles = fetch_google_news(max_pages=3)           
        image_path = generate_wordcloud(google_news_titles)          
        image_url = request.url_root.replace("http", "https") + "static/wordcloud.png"

        reply_messages.append(TextMessage(text=reply_text))
        reply_messages.append(ImageMessage(original_content_url=image_url, preview_image_url=image_url))

    elif postback_data == "查詢今日星座運勢":
        user_state[user_id] = "awaiting_zodiac"  # ✅ 設定用戶狀態，等待輸入星座
        reply_messages.append(TextMessage(text="🔎請輸入您要查詢的星座名稱（如：摩羯座、獅子座）"))

    elif postback_data == "查詢目前天氣資訊":
        user_state[user_id] = "awaiting_location"  # ✅ 設定狀態，等待用戶提供位置信息
        reply_messages.append(TextMessage(text="📍 請傳送您的 位置資訊，我會告訴你現在的天氣！ 🌦"))

    # 選擇 ConfirmTemplate 收入/支出
    elif postback_data.startswith("記帳"):
        parts = postback_data.split(",")
        if len(parts) == 4:
            _, record_type, category, amount = parts
            save_expense(category, amount, user_id, record_type)
            reply_messages.append(TextMessage(
                text=f"✅ 已記錄 {record_type}：{category} {amount} 元",
                quick_reply=expense_quickReply()
                ))
        else:
            reply_messages.append(TextMessage(text="⚠️ 記帳格式錯誤，請重新輸入！"))
            
    elif postback_data == "點我開始記帳":
        """好像有點太冗長
        reply_text = (
            "📌 記帳功能說明：\n"
            "請輸入「類別 + 金額」來記帳，例如：「餐飲 120」\n"
            "——————————————\n"
            "✅ 查詢記帳資訊：\n"
            "🔹查詢今日支出\n"
            "🔹查詢本週支出\n"
            "🔹查詢本月支出\n"
            "🔹查詢本月收入\n"
            "——————————————\n"
            "✅ 設定預算：\n"
            "🔹設定週預算\n"
            "🔹設定月預算"
        )
        """

        #reply_messages.append(TextMessage(text=reply_text))  # 先推播功能說明
        reply_messages.append(TextMessage(text="📌 請選擇記帳功能：", quick_reply=expense_quickReply()))  # 再推 Quick Reply

    elif postback_data in ["查詢今日支出", "查詢本週支出", "查詢本月支出", "查詢本月收入", "設定月預算", "設定週預算"]:
        user_id = event.source.user_id

        # 查詢功能
        if postback_data in ["查詢今日支出", "查詢本週支出", "查詢本月支出", "查詢本月收入"]:
            if postback_data == "查詢今日支出":
                reply_text = get_today_expense(user_id)
            elif postback_data == "查詢本週支出":
                reply_text = get_weekly_expense(user_id)
            elif postback_data == "查詢本月支出":
                reply_text = get_monthly_expense(user_id)
            elif postback_data == "查詢本月收入":
                reply_text = get_monthly_income(user_id)

            if not reply_text or reply_text.strip() == "":
                reply_text = "⚠️ 查詢失敗，請稍後再試，或確認是否有記帳記錄。"

            reply_messages.append(TextMessage(text=reply_text, quick_reply=expense_quickReply()))

        # 設定預算功能
        elif postback_data in ["設定月預算", "設定週預算"]:
            period = "monthly" if postback_data == "設定月預算" else "weekly"
            user_state[user_id] = f"awaiting_budget_{period}"
            reply_messages.append(TextMessage(text=f"💰 請輸入你的{postback_data}金額，例如：5000"))

    # 查詢關注股票清單
    elif postback_data == "查詢我的股票":
        user_id = event.source.user_id
        response = get_watchlist(user_id)  
        reply_messages.append(TextMessage(text=response))  # 不額外觸發stock_quickReply

    # "關注" 股票
    elif postback_data.startswith("watchlist,"):
        parts = postback_data.split(",")

        # 檢查長度
        if len(parts) < 3:
            reply_messages.append(TextMessage(text="⚠️ 無法解析股票資訊，請稍後再試。"))
            return

        _, stock_code, stock_name = parts
        result = add_watchlist(user_id, stock_code, stock_name)

        reply_messages.append(TextMessage(text=result))
        
        # 繼續詢問用戶是否要查詢更多
        reply_messages.append(TextMessage(text="📢 想知道更多？", quick_reply=stock_quickReply(stock_code, stock_name)))

    # "取消關注" 股票
    elif postback_data.startswith("unwatchlist,"):
        parts = postback_data.split(",")

        if len(parts) < 3:
            reply_messages.append(TextMessage(text="⚠️ 無法解析股票資訊，請稍後再試。"))
            return

        _, stock_code, stock_name = parts
        result = remove_watchlist(user_id, stock_code, stock_name)

        reply_messages.append(TextMessage(text=result))
        
        # 繼續詢問用戶是否要查詢更多
        reply_messages.append(TextMessage(text="📢 想知道更多？", quick_reply=stock_quickReply(stock_code, stock_name)))
     
    # 照片風格轉換   
    elif postback_data == "照片風格轉換":
        reply_messages.append(TextMessage(text="📸 請傳送照片並選擇風格來開始"))

    elif postback_data.startswith("filter"):
        _, filter_type, image_path = postback_data.split(",")

        # 確保圖片存在
        if not os.path.exists(image_path):
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="❌ 圖片已遺失，請重新上傳！")]
                )
            )
            return

        # 風格名稱對應表
        filter_names = {
            "sketch": "✏️ 素描風格",
            "emboss": "🖼️ 浮雕效果",
            "oil_paint": "🖌️ 油畫風格",
            "black_white": "📽️ 黑白復古",
            "soft_glow": "✨ 霧面柔化",
            "big_eyes": "👀 大眼特效"
        }

        selected_filter_name = filter_names.get(filter_type, "未知風格")

        # 讀取圖片
        img = cv2.imread(image_path)

        # 選擇風格
        if filter_type == "sketch":
            processed_img = sketch_effect(img)
        elif filter_type == "emboss":
            processed_img = emboss_effect(img)
        elif filter_type == "oil_paint":
            processed_img = oilPaint_effect(img)
        elif filter_type == "black_white":
            processed_img = blackWhite_effect(img)
        elif filter_type == "soft_glow":
            processed_img = softGlow_effect(img)
        elif filter_type == "big_eyes":
            processed_img = bigEyes_effect(img)
        else:
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="❌ 選擇的風格無效")]
                )
            )
            return


        # 儲存處理後的圖片
        output_path = image_path.replace(".jpg", f"_{filter_type}.jpg")
        cv2.imwrite(output_path, processed_img)

        # 轉換 URL 讓 Line Bot 可以回傳圖片
        image_url = f"{request.url_root}{output_path}".replace("http", "https")

        # 先回覆用戶選擇的風格
        reply_messages = [
            TextMessage(text=f"正在套用{selected_filter_name}，請稍後...⏳"),
            ImageMessage(original_content_url=image_url, preview_image_url=image_url)
        ]

        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=reply_messages
            )
        )
    # 相關新聞查詢
    elif postback_data.startswith("news,"):
        stock_code = postback_data.split(",")[1]
        stock_name = get_stock_name(stock_code)  # 先轉成中文名稱
        news_text = get_stock_news(stock_name)  # 用中文名稱查新聞

        # 回應新聞資訊
        reply_messages.append(TextMessage(text=news_text))

        # 繼續詢問用戶是否要查詢更多
        reply_messages.append(TextMessage(text="📢 想知道更多？", quick_reply=stock_quickReply(stock_code, stock_name)))


    # 走勢圖查詢
    elif postback_data.startswith("trend,"):
        # 檢查 `postback_data` 是否正確解析
        parts = postback_data.split(",")
        if len(parts) < 2:
            reply_messages.append(TextMessage(text="⚠️ 無法解析股票資訊，請稍後再試。"))
            return

        stock_code = parts[1]  # 取得股票代碼
        stock_name = parts[2] if len(parts) > 2 else stock_code  # 確保 stock_name存在

        # 生成走勢圖
        image_path = plot_stock_trend(stock_code)

        if not image_path:
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=f"⚠️ 無法取得 {stock_name}（{stock_code}）的走勢圖，請稍後再試！")]
                )
            )
            return

        # 轉換為 HTTPS 圖片 URL
        base_url = request.url_root.replace("http://", "https://").rstrip("/")
        image_filename = os.path.basename(image_path)  # 取得圖片檔名
        trend_chart_url = f"{base_url}/static/trend_chart/{image_filename}"

        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    ImageMessage(original_content_url=trend_chart_url, preview_image_url=trend_chart_url),
                    TextMessage(text="📢 想知道更多？", quick_reply=stock_quickReply(stock_code, stock_name))
                ]
            )
        )

    # K 線圖查詢
    elif postback_data.startswith("kchart,"):
        # 檢查 postback_data 是否正確解析
        parts = postback_data.split(",")
        if len(parts) < 2:
            reply_messages.append(TextMessage(text="⚠️ 無法解析股票資訊，請稍後再試。"))
            return

        stock_code = parts[1]  # 取得股票代碼
        stock_name = parts[2] if len(parts) > 2 else stock_code  # 確保 stock_name存在

        # 產生 K 線圖
        image_path = plot_stock_chart(stock_code)

        if not image_path:
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=f"⚠️ 無法取得 {stock_name}（{stock_code}）的 K 線圖，請稍後再試！")]
                )
            )
            return

        # 轉換為 HTTPS 圖片 URL
        base_url = request.url_root.replace("http://", "https://").rstrip("/")
        image_filename = os.path.basename(image_path)  # 取得圖片檔名
        image_url = f"{base_url}/static/kchart/{image_filename}"


        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    ImageMessage(original_content_url=image_url, preview_image_url=image_url),
                    TextMessage(text="📢 想知道更多？", quick_reply=stock_quickReply(stock_code, stock_name))
                ]
            )
        )

    # 重新查詢其他股票
    elif postback_data == "search_new_stock":
        reply_messages.append(TextMessage(text="🔍 請輸入新的股票代碼，例如：2330"))
    
    # 貓狗品種辨識
    elif postback_data.startswith("breed_detect"):
        parts = postback_data.split(",")  
        if len(parts) < 2:
            reply_text = "⚠️ 品種辨識發生錯誤，請重新上傳圖片！"
        else:
            image_path = parts[1]
            breed_en, breed_cn, confidence = predict_breed(image_path)   

            # 設定信心度門檻
            confidence_threshold = 0.6  # 50% 以下提醒用戶
            warning_text = "⚠️ 由於信心度較低，僅供參考，可能需要重新上傳更清晰的圖片！" if confidence < confidence_threshold else ""

            reply_text = (
                f"🔍 預測結果：\n"
                f"🐶🐱 牠可能是【{breed_cn} {breed_en}】\n"
                f"✨ 信心度：{confidence:.2%}\n"
                f"{warning_text}"
            )

        reply_messages.append(TextMessage(text=reply_text))


    if reply_messages:
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=reply_messages
            )
        )


if __name__ == "__main__":
    app.run(
        debug=True,    # 啟用除錯模式
        host="0.0.0.0", # 設定 0.0.0.0 會對外開放
        port=5000       # 啟用 port 號
    )
