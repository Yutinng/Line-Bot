"""爬蟲搜索Yahoo熱搜前10則熱門新聞"""

import requests
from bs4 import BeautifulSoup as bs

def get_real_news_url(newsurl):
    """
    爬取新聞的真實內部連結。
    若解析失敗，則回傳原始 URL。
    """
    try:
        data = requests.get(newsurl).text
        soup = bs(data, 'html.parser')

        title = soup.find('li', class_='ov-a fst')
        if title:
            link = title.find('a').get('href')
            return link 
        
    except Exception as e:
        print(f"無法解析新聞內部連結: {e}")

    return newsurl  # 若解析失敗，則返回原始 URL

def get_hot_news():
    """
    爬取 Yahoo 首頁的前 10 則熱搜新聞，並返回新聞標題與連結的列表。
    若抓取過程中出現錯誤，將拋出例外。
    """
    yahoo_url = 'https://tw.yahoo.com/'
    headers = {
        'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
    }

    try:
        res = requests.get(yahoo_url, headers=headers)
        res.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"網路請求失敗: {e}")
    
    soup = bs(res.text, "lxml")
  
    # 取得前10筆熱搜新聞
    hot_news = soup.select('div#header-search-keywords > span~a')[:10]
    
    if not hot_news:
        return "目前無法取得熱搜新聞，請稍後再試。"
    
    news_list = []                  # 用來存放爬取到的新聞標題

    for idx, news in enumerate(hot_news, start=1):
        # 取得新聞標題與連結
        title = news.get_text(strip=True)
        news_url = news.get('href')
        # 新聞的真實 URL
        real_news_url = get_real_news_url(news_url)
        
        news_str = (
            f"第{idx}則新聞：\n"
            f"標題：{title}\n"
            f"網址：{real_news_url}"
        )
        news_list.append(news_str)
    
    # 將所有新聞用換行區隔組合成一個字串返回
    return "\n\n".join(news_list)

# 測試
if __name__ == "__main__":
    print(get_hot_news())