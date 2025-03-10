"""
建立圖文選單 (Rich Menu)
"""
import os
import requests
import json
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    MessagingApiBlob,
)
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
configuration = Configuration(access_token=ACCESS_TOKEN)

def create_rich_menu():
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_blob_api = MessagingApiBlob(api_client)

        headers = {
            'Authorization': 'Bearer ' + ACCESS_TOKEN,
            'Content-Type': 'application/json'
        }

        body = {
            "size": {
                "width": 2500,
                "height": 1686
            },
            "selected": True,
            "name": "主選單",
            "chatBarText": "📌 查看更多功能",
            "areas": [
                {
                    "bounds": {"x": 0, "y": 0, "width": 824, "height": 832},
                    "action": {"type": "postback", "data": "查詢目前熱搜新聞"}
                },
                {
                    "bounds": {"x": 832, "y": 8, "width": 823, "height": 828},
                    "action": {"type": "postback", "data": "查詢今日星座運勢"}
                },
                {
                    "bounds": {"x": 1677, "y": 4, "width": 823, "height": 828},
                    "action": {"type": "postback", "data": "查詢目前天氣資訊"}
                },
                {
                    "bounds": {"x": 4, "y": 849, "width": 824, "height": 832},
                    "action": {"type": "postback", "data": "點我開始記帳"}
                },
                {
                    "bounds": {"x": 849, "y": 857, "width": 811, "height": 824},
                    "action": {"type": "postback", "data": "照片風格轉換"}
                },
                {
                    "bounds": {"x": 1677, "y": 861, "width": 823, "height": 820},
                    "action": {"type": "message", "text": "查詢我的股票"}
                }
            ]
        }

        response = requests.post(
            'https://api.line.me/v2/bot/richmenu',
            headers=headers,
            data=json.dumps(body).encode('utf-8')
        )
        response_data = response.json()
        print("📌 Rich Menu Response:", response_data)

        if "richMenuId" not in response_data:
            print("❌ 建立 Rich Menu 失敗，請檢查錯誤訊息！")
            return

        rich_menu_id = response_data["richMenuId"]
        print("✅ Rich Menu 建立成功！Rich Menu ID:", rich_menu_id)

        try:
            with open('static/richmenu.jpg', 'rb') as image:
                line_bot_blob_api.set_rich_menu_image(
                    rich_menu_id=rich_menu_id,
                    body=bytearray(image.read()),
                    _headers={'Content-Type': 'image/jpeg'}
                )
            print("✅ Rich Menu 圖片上傳成功！")
        except FileNotFoundError:
            print("❌ 找不到 `static/richmenu-1.jpg`，請確認圖片檔案是否存在！")
            return

        line_bot_api.set_default_rich_menu(rich_menu_id)
        print("✅ Rich Menu 設定為預設選單！")

if __name__ == "__main__":
    create_rich_menu()
