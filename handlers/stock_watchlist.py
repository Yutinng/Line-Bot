import os
from pymongo import MongoClient
from get_username import get_line_username
import yfinance as yf
import datetime
import numpy as np

# MongoDB 連接設定
client = MongoClient(os.getenv('MONGO_URI'))
db = client["linebot"]
collection = db["watchlist"]

def add_watchlist(user_id, stock_code, stock_name):
    """
    新增使用者關注的股票到 MongoDB
    :param user_id: LINE 用戶 ID
    :param stock_code: 股票代碼
    :param stock_name: 股票名稱
    :return: 回傳成功或失敗訊息
    """
    try:
        # 檢查用戶是否已經關注該股票
        existing_stock = collection.find_one({"user_id": user_id, "stock_code": stock_code})

        if existing_stock:  # 如果該股票已經在關注清單，直接回傳訊息
            return f"⚠️ 你已經關注 {stock_code}（{stock_name}）了！"

        # 取得用戶最新名稱
        user_name = get_line_username(user_id)

        # 插入新股票
        collection.insert_one({
            "user_id": user_id,
            "user_name": user_name,  
            "stock_code": stock_code,
            "stock_name": stock_name
        })
        return f"✅ 成功關注 {stock_code}（{stock_name}）！"

    except Exception as e:
        return f"❌ 無法加入關注清單：{str(e)}"


def handle_add_watchlist(event, stock_code, stock_name):
    """
    處理 Line Bot 來的「關注股票」請求
    :param event: LINE Bot 事件（包含 user_id）
    :param stock_code: 股票代碼
    :param stock_name: 股票名稱
    :return: 回傳訊息給用戶
    """
    user_id = event.source.user_id  # 取得 LINE 用戶 ID
    response = add_watchlist(user_id, stock_code, stock_name)
    return response

# 取消關注股票
def remove_watchlist(user_id, stock_code, stock_name):
    """
    從 MongoDB 移除使用者關注的股票
    """
    try:
        # 確認該股票是否存在於關注清單
        existing_stock = collection.find_one({"user_id": user_id, "stock_code": stock_code})
        
        if not existing_stock:
            return f"⚠️ 你尚未關注 {stock_name}（{stock_code}），無法取消！"

        # 執行刪除
        result = collection.delete_one({"user_id": user_id, "stock_code": stock_code})
        if result.deleted_count > 0:
            return f"✅ 已成功將 {stock_name}（{stock_code}）從關注清單移除！"
        else:
            return f"⚠️ 你尚未關注 {stock_name}（{stock_code}），無法取消！"

    except Exception as e:
        return f"❌ 無法取消關注：{str(e)}"


# 股票基本資料
def get_stockdata(stock_code):
    """
    從 Yahoo Finance 取得台股完整股價數據，包含：
    - 最新價格
    - 漲跌與漲跌百分比
    - 近五日平均價與標準差
    """
    try:
        # 抓取最近 6 天的數據（確保至少有 5 天交易數據）
        stock = yf.Ticker(f"{stock_code}.TW")
        df = stock.history(period="6d")  

        if df.empty or len(df) < 2:
            return {"error": f"找不到 {stock_code} 的股票數據"}

        # 取得最新數據
        last_data = df.iloc[-1]
        prev_data = df.iloc[-2] if len(df) > 1 else last_data  # 前一天數據，避免數據缺失

        # 計算漲跌 & 漲跌百分比
        price_change = last_data["Close"] - prev_data["Close"]
        percentage_change = (price_change / prev_data["Close"]) * 100 if prev_data["Close"] > 0 else "N/A"

        # 計算近五日平均價 & 標準差
        avg_price_5d = df["Close"].tail(5).mean() if len(df) >= 5 else "N/A"
        std_dev_5d = np.std(df["Close"].tail(5)) if len(df) >= 5 else "N/A"

        return {
            "latest_price": last_data["Close"],  # 最新收盤價
            "open_price": last_data["Open"],  # 開盤價
            "high_price": last_data["High"],  # 最高價
            "low_price": last_data["Low"],  # 最低價
            "price_change": round(price_change, 2) if price_change != "N/A" else "N/A",
            "percentage_change": round(percentage_change, 2) if percentage_change != "N/A" else "N/A",
            "avg_price_5d": round(avg_price_5d, 2) if avg_price_5d != "N/A" else "N/A",
            "std_dev_5d": round(std_dev_5d, 2) if std_dev_5d != "N/A" else "N/A",
            "date": datetime.datetime.today().strftime("%Y-%m-%d") 
        }

    except Exception as e:
        return {"error": f"獲取股市數據失敗: {str(e)}"}


# 查詢已關注的股票
def get_watchlist(user_id):
    """
    查詢使用者關注的所有股票，包含完整技術指標資訊
    """
    try:
        stocks = collection.find({"user_id": user_id})
        stock_list = list(stocks)

        if not stock_list:
            return "⚠️你目前沒有關注任何股票！"

        message = ""

        for stock in stock_list:
            stock_code = stock['stock_code']
            stock_name = stock['stock_name']

            stock_data = get_stockdata(stock_code)

            if "error" in stock_data:
                message += f"\n⚠️ {stock_name}（{stock_code}）資訊查詢失敗\n"
                continue
            
            message += f"📌{stock_code}—{stock_name}：\n"
            message += f"日期: {stock_data['date']}\n"
            message += f"🔹 最新收盤價: {stock_data['latest_price']:.2f} 元\n"
            message += f"🔹 開盤價: {stock_data['open_price']:.2f} 元\n"
            message += f"🔹 最高價: {stock_data['high_price']:.2f} 元\n"
            message += f"🔹 最低價: {stock_data['low_price']:.2f} 元\n"
            message += f"🔹 漲跌: {'🔺' if stock_data['price_change'] != 'N/A' and stock_data['price_change'] > 0 else '🔻'} {stock_data['price_change']:.2f} 元 ({stock_data['percentage_change']:.2f}%)  \n"
            message += f"🔹 近五日平均價: {stock_data['avg_price_5d']:.2f} 元  \n"
            message += f"🔹 近五日標準差: {stock_data['std_dev_5d']:.2f}  \n"
            message += f"———————————————\n"


        return message.strip()

    except Exception as e:
        return f"❌ 查詢關注股票時發生錯誤：{str(e)}"


# 測試
if __name__ == "__main__":
    user_id = "test_user_123"  
    stock_code = "2330"
    stock_name = "台積電"
    print(add_watchlist(user_id, stock_code, stock_name))




