"""
抓取 Google 搜尋:'新聞'時所出現的前3頁(共30則)新聞標題,將其匯出文字雲傳給用戶
"""

import requests
from bs4 import BeautifulSoup
import jieba
import jieba.analyse
import re
from wordcloud import WordCloud
import numpy as np
import matplotlib
matplotlib.use('Agg')  
import matplotlib.pyplot as plt
import os
from PIL import Image, ImageDraw

# Google 新聞 URL，變更 start 參數進行翻頁，取得多頁新聞標題
google_url = "https://www.google.com/search?q=新聞&tbm=nws&start={}"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
}

def fetch_google_news(max_pages=3):
    """ 爬取 Google 新聞標題，最多爬取 3 頁 """
    google_news = []
    for page in range(max_pages):
        start = page * 10
        new_googleurl = google_url.format(start)
        print(f"爬取第 {page+1} 頁：{new_googleurl}")
        try:
            res = requests.get(new_googleurl, headers=headers)
            res.raise_for_status()
        except requests.RequestException as e:
            print(f"無法取得新聞：{e}")
            break  
        soup = BeautifulSoup(res.text, "lxml")
        articles = soup.select("div.SoAPf > div.n0jPhd.ynAwRc.MBeuO.nDgy9d")  
        if not articles:
            print("找不到新聞標題，我爆炸了")
            break
        for article in articles:
            title = article.get_text(strip=True)  
            google_news.append(title)  
        print(f"成功抓取 {len(articles)} 則新聞標題\n") 
    return google_news  

def load_stopwords(filepath=r"stopwords-master/stopwords.txt"):
    """ 使用停用詞表過濾無意義詞，增加文字雲關鍵詞準確度 """
    stopwords = set()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                stopwords.add(line.strip())
    except FileNotFoundError:
        print(f"找不到停用詞表：{filepath}")  
    return stopwords

def create_circle_mask(size):
    """ 產生無邊框的圓形遮罩，使文字雲為圓形 """
    mask = Image.new("L", size, 255)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size[0], size[1]), fill=0)
    return np.array(mask)

def generate_wordcloud(news_titles):
    """ 產生 Google 新聞標題的熱搜文字雲 """
    print("正在生成新聞熱搜文字雲...")
    if not news_titles:
        print("新聞標題抓取失敗，無法生成文字雲！")
        return  

    text = " ".join(news_titles)
    text = re.sub(r'[^\w\s]', '', text)
    stopwords = load_stopwords()
    words = jieba.lcut(text, cut_all=False)
    word_freq = {}
    for word in words:
        if len(word) > 1 and word not in stopwords:
            word_freq[word] = word_freq.get(word, 0) + 1

    tfidf_keywords = jieba.analyse.extract_tags(text, topK=100, withWeight=False)
    combined_keywords = [word for word in tfidf_keywords if word in word_freq]
    cleaned_text = " ".join(combined_keywords)
    
    mask = create_circle_mask((800, 800))

    wordcloud = WordCloud(
        font_path="msjh.ttc",
        width=800, 
        height=800,
        background_color="white",
        max_words=100,
        colormap="copper",  
        contour_width=0,
        mask=mask,
        collocations=False,
        stopwords=stopwords,
        prefer_horizontal=0.9  # 增加文字橫向排列的機率，減少直向字體
    ).generate(cleaned_text)

    save_path = "static/wordcloud.png"
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    if os.path.exists(save_path):
        os.remove(save_path)
    
    plt.figure(figsize=(8, 8))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis("off")
    plt.savefig(save_path, dpi=300, bbox_inches='tight', transparent=True)
    plt.close()
    
    print(f"文字雲圖片已保存至 {save_path}")
    return save_path

if __name__ == "__main__":
    news_titles = fetch_google_news(max_pages=3)
    if news_titles:
        img_path = generate_wordcloud(news_titles)
        print(f"文字雲圖片已生成，存放於：{img_path}")
    else:
        print("未能獲取新聞標題，請檢查爬取部分")
