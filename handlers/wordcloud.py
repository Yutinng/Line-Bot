"""
當用戶輸入："新聞" :
抓取 Google 搜尋:'新聞'時所出現的前3頁(共30則)新聞標題,將其匯出文字雲傳給用戶
"""

import requests
from bs4 import BeautifulSoup
import jieba
import jieba.analyse
import re
from wordcloud import WordCloud
import os

# 抓取Google 搜尋新聞時的URL，變更 start 參數進行翻頁，取得多頁新聞標題
google_url = "https://www.google.com/search?q=新聞&sca_esv=eeb9c8b046420867&tbm=nws&start={}"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
}

def fetch_google_news(max_pages=3):
    """
    爬取 Google 新聞標題，最多爬取 3 頁
    """
    google_news = []  # 用來存放爬取到的新聞標題

    for page in range(max_pages):
        start = page * 10                                     # 計算每頁對應的 `start` 參數（如 0, 10, 20, ...）
        new_googleurl = google_url.format(start)              # 產生對應頁數的 Google 新聞 URL
        print(f"爬取第 {page+1} 頁：{new_googleurl}")         

        try:
            response = requests.get(new_googleurl, headers=headers)  
            response.raise_for_status()                               # 若請求失敗則拋出錯誤
        except requests.RequestException as e:
            print(f"無法取得新聞：{e}")
            break  

        soup = BeautifulSoup(response.text, "lxml")  
        
        articles = soup.select("div.SoAPf > div.n0jPhd.ynAwRc.MBeuO.nDgy9d")  

        if not articles:
            print("找不到新聞標題，我爆炸了")
            break

        for article in articles:
            title = article.get_text(strip=True)  
            google_news.append(title)  

        print(f"成功抓取 {len(articles)} 則新聞標題\n") 

    return google_news  # 回傳爬取到的新聞標題列表

def load_stopwords(filepath=r"stopwords-master/baidu_stopwords.txt"):
    """
    使用停用詞表過濾無意義詞，增加文字雲關鍵詞準確度
    """
    stopwords = set(["新聞","快訊"])  # 預設將「新聞」視為停用詞
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                stopwords.add(line.strip().lower())  # 去除空格 & 轉小寫
    except FileNotFoundError:
        print(f"找不到停用詞表：{filepath}")  
    return stopwords

def generate_wordcloud(news_titles):
    """
    產生 Google 新聞標題的熱搜文字雲
    """
    print("正在生成新聞熱搜文字雲...")

    if not news_titles:
        print("新聞標題抓取失敗，無法生成文字雲！")
        return  

    # 將所有新聞標題合併為單一字串，移除標點符號,只保留文字
    text = " ".join(news_titles)
    text = re.sub(r'[^\w\s]', '', text) 

    # 使用 TF-IDF 取得前 50 個最重要的關鍵詞
    stopwords = load_stopwords()
    keywords = jieba.analyse.extract_tags(text, topK=50, withWeight=False)

    # 過濾停用詞
    filtered_keywords = [word for word in keywords if word not in stopwords]

    # 將關鍵詞組合成新的文字內容
    cleaned_text = " ".join(filtered_keywords)

    # 產生文字雲
    wordcloud = WordCloud(
        font_path="msjh.ttc",  # 設定字體
        width=900, height=500, background_color="black",colormap="viridis"
    ).generate(cleaned_text)

    # 設定存檔位置
    save_path = "static/wordcloud.png"  
    os.makedirs(os.path.dirname(save_path), exist_ok=True) 

    # 檢查是否有舊檔案，有就刪除
    if os.path.exists(save_path):
        os.remove(save_path)

    # 儲存新圖片
    wordcloud.to_file(save_path)  

    return save_path  





