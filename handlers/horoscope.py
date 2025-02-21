""""
當用戶輸入"查詢今日星座運勢"時，
爬取對應星座運勢並返回給用戶
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin  # 拼接 URL
from datetime import datetime



horoscope_URL = "https://www.elle.com"

def get_horoscope_content(user_zodiac):
    """ 爬取 ELLE 星座運勢（返回整體運勢、愛情、事業、財運） """
    
    # 目標網頁
    allhor_url = urljoin(horoscope_URL, "/tw/starsigns/")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"}

    response = requests.get(allhor_url, headers=headers)
    if response.status_code != 200:
        return f"❌ 無法取得主頁，狀態碼：{response.status_code}"
    
    soup = BeautifulSoup(response.text, "html.parser")

    # 選擇對應星座的 HTML 元素
    zodiac_selector = f'[data-theme-key="custom-item"][data-vars-cta="今日運勢"][data-vars-ga-call-to-action="{user_zodiac}"]'
    zodiac_element = soup.select_one(zodiac_selector)

    if not zodiac_element:
        return f"⚠️ 找不到 {user_zodiac} 的運勢頁面，請檢查輸入的星座名稱！"

    zodiac_path = zodiac_element["href"]
    zodiac_url = urljoin(horoscope_URL, zodiac_path)  # 拼接完整 URL

    
    zodiac_response = requests.get(zodiac_url, headers=headers)
    if zodiac_response.status_code != 200:
        return f"❌ 無法取得 {user_zodiac} 的運勢頁面，狀態碼：{zodiac_response.status_code}"

    zodiac_soup = BeautifulSoup(zodiac_response.text, "html.parser")

    # 抓取整體運勢
    fortune_selector = '[data-journey-content="true"][data-node-id="4"]'
    fortune_element = zodiac_soup.select_one(fortune_selector)
    fortune_text = fortune_element.get_text(strip=True) if fortune_element else "找不到整體運勢內容。"

    # 抓取愛情運勢
    love_selector = "p:nth-child(11)"  
    love_element = zodiac_soup.select_one(love_selector)
    love_text = love_element.get_text(strip=True) if love_element else "找不到愛情運勢內容。"

    # 抓取事業運勢
    career_selector = "p:nth-child(15)" 
    career_element = zodiac_soup.select_one(career_selector)
    career_text = career_element.get_text(strip=True) if career_element else "找不到事業運勢內容。"

    # 抓取財運運勢
    wealth_selector = "p:nth-child(19)"  
    wealth_element = zodiac_soup.select_one(wealth_selector)
    wealth_text = wealth_element.get_text(strip=True) if wealth_element else "找不到財運運勢內容。"


    today_date = datetime.today().strftime("%m月%d日")
    return (
        f"🔮 {user_zodiac} 今日運勢\n"
        f"📅 日期：{today_date}\n"
        f"——————————————\n"
        f"📌 整體運勢：{fortune_text}\n"
        f"❤️ 愛情運勢：{love_text}\n"
        f"💼 事業運勢：{career_text}\n"
        f"💰 財運運勢：{wealth_text}\n"
        f"🔗 [查看完整運勢]({zodiac_url})"
    )
