import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import datetime
import os
from handlers.stock_prediction import get_stock_name  

# 設定字體
font_path = "msjh.ttf"  # 微軟正黑體
if not os.path.exists(font_path):
    raise FileNotFoundError(f"找不到字體檔案: {font_path}")

my_font = fm.FontProperties(fname=font_path, size=12)

# 設定圖片儲存路徑
SAVE_DIR = "static/trend_chart"
os.makedirs(SAVE_DIR, exist_ok=True)

def plot_stock_trend(stock_code):
    """
    繪製股票趨勢圖（1 個月），並儲存為圖片。
    :param stock_code: 股票代碼（如 "2330"）
    """
    try:
        # 抓取股票數據（最近 1 個月）
        stock = yf.Ticker(f"{stock_code}.TW")
        df = stock.history(period="3mo")

        if df.empty:
            print(f"❌ 找不到 {stock_code} 的股票數據")
            return None
        
        # 取得股票中文名稱
        stock_name = get_stock_name(stock_code)
        
        # 計算 5 日、20 日均線
        df["MA5"] = df["Close"].rolling(window=5).mean()
        df["MA20"] = df["Close"].rolling(window=20).mean()

        # 取得最新日期
        last_date = df.index[-1].strftime("%Y-%m-%d")
        today_date = datetime.datetime.today().strftime("%Y-%m-%d")

        # 建立圖表
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(df.index, df['Close'], label="收盤價", color='blue', linewidth=1.5)
        ax.plot(df.index, df['MA5'], label="MA5", color='orange', linestyle='dashed', linewidth=1)
        ax.plot(df.index, df['MA20'], label="MA20", color='red', linestyle='dashed', linewidth=1)

        # 設定標題與軸標籤
        ax.set_title(f"{stock_code} {stock_name}－股票走勢圖 (3 個月)", fontproperties=my_font, fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel("日期", fontproperties=my_font, fontsize=12)
        ax.set_ylabel("股價 (TWD)", fontproperties=my_font, fontsize=12)
        ax.legend(prop=fm.FontProperties(fname=font_path, size=9))
        ax.grid()

        # 調整 X 軸標籤格式，避免被切到
        fig.autofmt_xdate()
        plt.subplots_adjust(bottom=0.2)  # 增加底部間距，確保日期完整顯示
        
        # 移動圖例到圖表內左上角
        ax.legend(prop=fm.FontProperties(fname=font_path, size=10), loc='upper left', frameon=True)

        # 顯示擷取日期
        date_text = f"製表日期: {today_date}\n數據截止日: {last_date}" 
        ax.text(1, 1.08, date_text, transform=ax.transAxes,
                fontsize=10, fontproperties=my_font, color="black",
                verticalalignment='top', horizontalalignment='right')

        # 儲存圖片
        img_path = os.path.join(SAVE_DIR, f"{stock_code}.png")
        fig.savefig(img_path, dpi=300)
        print(f"✅ 股票走勢圖已儲存: {img_path}")

        return img_path

    except Exception as e:
        print(f"⚠️ 發生錯誤: {e}")
        return None

# 測試
if __name__ == "__main__":
    stock_code = "2330"
    plot_stock_trend(stock_code)
