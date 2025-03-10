from gnews import GNews

def get_stock_news(stock_code):
    """
    使用 GNews 搜尋特定股票的新聞，直接回傳文字格式的標題與連結
    """
    google_news = GNews(language='zh', country='TW', max_results=5)   # 設定台灣、中文、最多 5 篇新聞
    news_results = google_news.get_news(stock_code)                   # 用股票名稱查詢新聞
    
    if not news_results:
        return f"⚠️ 沒有找到 {stock_code} 的相關新聞。"
    
    news_text = f"📰 {stock_code} 相關新聞：\n"
    for i, news in enumerate(news_results[:5], 1):  # 取前 5 則新聞
        title = news.get("title", "無標題新聞")
        url = news.get("url", "https://www.google.com/search?q=" + stock_code)
        news_text += f"{i}. {title}\n🔗 {url}\n\n"
    
    return news_text
