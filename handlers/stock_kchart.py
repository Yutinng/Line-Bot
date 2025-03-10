import yfinance as yf
import mplfinance as mpf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import datetime
import os
from handlers.stock_prediction import get_stock_name
#from stock_prediction import get_stock_name    # 測試用


# 確保字體檔案存在
font_path = "msjh.ttf"  # 微軟正黑體
if not os.path.exists(font_path):
    raise FileNotFoundError(f"找不到字體檔案: {font_path}")

# 設定字體
my_font = fm.FontProperties(fname=font_path, size=12)  # 字體稍微調整

# 設定圖片儲存路徑
SAVE_DIR = "static/kchart"
os.makedirs(SAVE_DIR, exist_ok=True)

def plot_stock_chart(stock_code):
    """
    繪製優化後的股票 K 線圖，將圖例移到底部，標題使用股票名稱
    :param stock_code: 股票代碼（如 "2330"）
    """
    try:
        # 抓取股票數據（最近 3 個月）
        stock = yf.Ticker(f"{stock_code}.TW")
        df = stock.history(period="3mo")

        if df.empty:
            print(f"❌ 找不到 {stock_code} 的股票數據")
            return None

        # 取得股票中文名稱
        stock_name = get_stock_name(stock_code)
        if "查詢失敗" in stock_name:
            stock_name = f"{stock_code}"  # 如果查不到名稱，就只顯示代碼

        # 調整資料格式
        df.index = pd.to_datetime(df.index)
        df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'}, inplace=True)

        # 取最後一筆數據（最新交易日）
        last_date = df.index[-1].strftime("%Y-%m-%d")  # 擷取日期（數據的最後一天）
        today_date = datetime.datetime.today().strftime("%Y-%m-%d")  # 製表日期（今天）

        last_data = df.iloc[-1]
        open_price = last_data["open"]
        close_price = last_data["close"]
        high_price = last_data["high"]
        low_price = last_data["low"]

        # 設定 K 線圖樣式
        mc = mpf.make_marketcolors(up='red', down='green', edge='black', wick='black', volume={'up': 'red', 'down': 'green'})
        s = mpf.make_mpf_style(base_mpf_style='yahoo', marketcolors=mc, gridcolor="gray", gridstyle="dotted")

        kwargs = dict(
            type='candle',
            mav=(5, 20),  # 5 日、20 日均線
            volume=True,
            figratio=(12, 6),
            figscale=1.3,
            style=s
        )

        # 建立圖表
        fig, axlist = mpf.plot(df, **kwargs, returnfig=True)

        # 調整標題
        axlist[0].set_title(f"{stock_code} {stock_name} K 線圖", fontproperties=my_font, fontsize=16, fontweight='bold', pad=30)

        # 減少左側留白，並讓 X 軸對齊右邊
        fig.subplots_adjust(left=0.1, right=0.95, top=0.9, bottom=0.3)  # bottom 增加以對齊 X 軸

        # 設定 Y 軸標籤
        axlist[0].set_ylabel("股價 (TWD)", fontproperties=my_font, fontsize=12, labelpad=10)
        axlist[2].set_ylabel("成交量", fontproperties=my_font, fontsize=12, labelpad=10)

        # 讓 X 軸日期標籤右對齊圖表
        axlist[0].xaxis.set_major_locator(plt.MaxNLocator(6))  # 設定最大標籤數

        # 調整 X 軸標籤
        for ax in axlist:
            for label in ax.get_xticklabels():
                label.set_rotation(30)
                label.set_fontsize(10)
                label.set_fontproperties(my_font)
                label.set_horizontalalignment('right')  # 讓日期向右對齊

        # 黃色框（當日價格資訊）
        text_info = f"開盤: {open_price:.1f}  收盤: {close_price:.1f}\n" \
                    f"最高: {high_price:.1f}  最低: {low_price:.1f}"
        axlist[0].text(0.02, 1.05, text_info, transform=axlist[0].transAxes,
                       fontsize=12, fontproperties=my_font,
                       bbox=dict(facecolor="yellow", edgecolor="black", boxstyle="round,pad=0.5"))

        # 在 K 線圖外面右上角顯示 擷取日期 & 製表日期
        date_text = f"製表日期: {today_date}\n數據截止日: {last_date}\n"
        axlist[0].text(0.95, 0.97, date_text, transform=axlist[0].transAxes,
                       fontsize=11, fontproperties=my_font, color="black")

        # 移動均線圖例到底部
        legend_lines = [
            plt.Line2D([0], [0], color='blue', lw=2, label="MA5"),
            plt.Line2D([0], [0], color='orange', lw=2, label="MA20"),
        ]
        axlist[0].legend(handles=legend_lines, loc="lower center", fontsize=10, frameon=True, prop=my_font, bbox_to_anchor=(0.95, -0.65))  # 圖例移到底部
        # 儲存圖片
        img_path = os.path.join(SAVE_DIR, f"{stock_code}.png")
        fig.savefig(img_path, dpi=300)
        print(f"✅ 圖片已儲存: {img_path}")

        return img_path

    except Exception as e:
        print(f"⚠️ 發生錯誤: {e}")
        return None

# 測試
if __name__ == "__main__":
    stock_code = "2330"  
    plot_stock_chart(stock_code)
