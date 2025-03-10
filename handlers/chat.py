"""Google Bard 回應用戶輸入其它問題"""

import google.generativeai as genai
import os


# 設定 Google Gemini API
genai.configure(api_key=os.getenv('GOOGLE_API_KEY2'))

def chat_with_bard(user_input):
    """使用 Google Gemini 1.5 Pro 回應用戶問題"""
    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(user_input)
        return response.text.strip() if response and hasattr(response, 'text') else "❌ 抱歉，我現在無法回應您的問題。"
    except Exception as e:
        print(f"Google Bard API 錯誤: {e}")
        return "❌ 抱歉，我現在無法回應您的問題。"
