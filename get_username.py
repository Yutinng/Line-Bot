"""
取得使用者 LINE 名稱
"""
import os
from linebot.v3.messaging import ApiClient, MessagingApi, Configuration

configuration = Configuration(access_token=os.getenv('ACCESS_TOKEN'))

def get_line_username(user_id):
    """
    透過 Line Messaging API 獲取用戶名稱
    """
    try:
        # 確保 API 物件正確初始化
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)

            # 取得用戶資料
            profile = line_bot_api.get_profile(user_id)
            return profile.display_name  # 回傳用戶名稱

    except Exception as e:
        print(f"❌ 獲取用戶名稱失敗: {e}") 
        return f"UnknownUser-{user_id[:6]}"  # 如果 API 失敗，回傳部分 user_id 以避免資料混亂
