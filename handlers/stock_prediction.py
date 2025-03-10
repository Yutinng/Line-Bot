"""
股價預測
"""

import os
import datetime
import twstock
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import load_model, Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Bidirectional
import ta        # 技術指標庫
import requests
import yfinance as yf
import pandas as pd
import numpy as np


def get_stock_name(stock_code):
    """ 從台灣證券交易所 API 取得股票名稱 """
    url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_{stock_code}.tw"
    
    try:
        response = requests.get(url)
        data = response.json()

        if "msgArray" in data and len(data["msgArray"]) > 0:
            return data["msgArray"][0]["n"]  # 取得股票名稱
        return "未知股票"
    except Exception as e:
        return f"查詢失敗：{str(e)}"


def get_technical_indicators(stock_code):
    """ 取得股票技術指標（均線、RSI、MACD） """
    stock = yf.Ticker(f"{stock_code}.TW")
    df = stock.history(period="6mo")

    if len(df) < 30:
        df = stock.history(period="12mo")

    if df.empty:
        return {"error": "無法獲取股價數據"}

    df["Close"] = df["Close"].ffill()

    # 計算均線
    df["MA5"] = df["Close"].rolling(window=5).mean()
    df["MA20"] = df["Close"].rolling(window=20).mean()

    # 計算 RSI
    if len(df) >= 14:
        delta = df["Close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=14, min_periods=14).mean()
        avg_loss = loss.rolling(window=14, min_periods=14).mean()

        rs = avg_gain / avg_loss
        df["RSI"] = 100 - (100 / (1 + rs))

        if df["RSI"].isna().all():
            return {"error": "⚠️ RSI 計算失敗，數據異常"}

    else:
        return {"error": "⚠️ 股票數據不足，無法計算 RSI"}

    # 計算 MACD
    short_ema = df["Close"].ewm(span=12, adjust=False).mean()
    long_ema = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = short_ema - long_ema
    df["MACD_SIGNAL"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_HIST"] = df["MACD"] - df["MACD_SIGNAL"]  # 柱狀圖

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    # 計算成交量變化
    df["Volume_MA5"] = df["Volume"].rolling(window=5).mean()
    volume_surge = latest["Volume"] > df["Volume_MA5"].iloc[-1] * 1.5  # 異常放量

    # 技術指標訊號
    signals = []
    signals.append("技術指標訊號：")
    signals.append(f"🔹 MA5：{latest['MA5']:.2f}  |  MA20：{latest['MA20']:.2f}")
    signals.append(f"🔹 RSI：{latest['RSI']:.2f}")
    signals.append(f"🔹 MACD：{latest['MACD']:.2f}  |  信號線：{latest['MACD_SIGNAL']:.2f}")

    if latest["MA5"] > latest["MA20"] and prev["MA5"] <= prev["MA20"]:
        signals.append("✅ MA5 上穿 MA20（黃金交叉）")
    if latest["MA5"] < latest["MA20"] and prev["MA5"] >= prev["MA20"]:
        signals.append("❌ MA5 下穿 MA20（死亡交叉）")
    if latest["RSI"] < 30:
        signals.append("✅ RSI < 30，超賣區，可能反彈")
    if latest["RSI"] > 70:
        signals.append("❌ RSI > 70，超買區，可能回調")
    if latest["MACD"] > latest["MACD_SIGNAL"] and prev["MACD"] <= prev["MACD_SIGNAL"]:
        signals.append("✅ MACD 黃金交叉（買入訊號）")
    if latest["MACD"] < latest["MACD_SIGNAL"] and prev["MACD"] >= prev["MACD_SIGNAL"]:
        signals.append("❌ MACD 死亡交叉（賣出訊號）")

    # 建議與操作建議
    recommendation = "📢 建議：市場觀望，趨勢不明"
    operation_advice = ""

    # 買入訊號
    if latest["MA5"] > latest["MA20"] and latest["RSI"] > 40 and latest["RSI"] < 60:
        recommendation = "📈 建議：買入"
        operation_advice = f"🔍 操作建議：若 RSI 突破 60，或價格站穩 MA5（{latest['MA5']:.2f}），可考慮進場"

    # 賣出訊號
    elif latest["MA5"] < latest["MA20"] and latest["RSI"] > 40 and latest["RSI"] < 60:
        recommendation = "📉 建議：賣出"
        operation_advice = f"🔍 操作建議：若 RSI 跌破 40，或價格跌破 MA5（{latest['MA5']:.2f}），可考慮減倉"

    # 持續觀察
    elif latest["RSI"] > 70 and latest["MA5"] > latest["MA20"] and volume_surge:
        recommendation = "⚠️ 建議：持續觀察"
        operation_advice = f"🔍 操作建議：若 RSI 回落至 65 以下，或價格跌破 MA5（{latest['MA5']:.2f}），應設停利點"

    elif latest["RSI"] < 30 and latest["MA5"] < latest["MA20"] and not volume_surge:
        recommendation = "⚠️ 建議：持續觀察"
        operation_advice = f"🔍 操作建議：若 RSI 回升至 35 以上，或價格突破 MA5（{latest['MA5']:.2f}），可能是短期反彈"

    # MACD 交叉作為趨勢確認
    elif latest["MACD"] > latest["MACD_SIGNAL"] and latest["RSI"] > 50:
        recommendation = "📈 建議：買入"
        operation_advice = f"🔍 操作建議：若價格站穩 MA20（{latest['MA20']:.2f}），確認支撐，則可進場"

    elif latest["MACD"] < latest["MACD_SIGNAL"] and latest["RSI"] < 50:
        recommendation = "📉 建議：賣出"
        operation_advice = f"🔍 操作建議：若價格跌破 MA20（{latest['MA20']:.2f}），趨勢確認轉弱，應考慮停損"

    signals.append("------------------------------")
    signals.append(recommendation)
    if operation_advice:
        signals.append(operation_advice)

    return {
        "latest_price": round(latest["Close"], 2),
        "signals": "\n".join(signals),  # **讓 signals 變成完整結果**
        "recommendation": recommendation
    }

    
def is_trading_day():
    """ 檢查今天是否為交易日（台灣證券交易所 API）"""
    today = datetime.date.today()
    weekday = today.weekday()  # 0=星期一, 4=星期五, 5=星期六, 6=星期日

    if weekday >= 5:  # 週六 & 週日不是交易日
        return False

    url = f"https://www.twse.com.tw/holidaySchedule/holidaySchedule?response=json&year={today.year}"
    
    try:
        response = requests.get(url)
        data = response.json()
        if "data" in data:
            holidays = [datetime.datetime.strptime(d[0], "%Y/%m/%d").date() for d in data["data"]]
            return today not in holidays
    except:
        return True  # 無法查詢時，預設為交易日

    return True

# 一次查詢多支股票
def predict_multiple_stocks(stock_codes):
    predictions = {}
    for stock_code in stock_codes:
        try:
            predictions[stock_code] = predict_stock_price(stock_code)
        except Exception as e:
            predictions[stock_code] = f"錯誤：{str(e)}"
    return predictions

def predict_stock_price(stock_code):
    model_path = f"models/{stock_code}_lstm_model.h5"

    # 1️⃣ 檢查今天是否為交易日
    if not is_trading_day():
        # 今天不是交易日，直接返回最後一次預測的價格
        if os.path.exists(model_path):
            last_predicted_price = np.load(f"models/{stock_code}_last_pred.npy")
            return last_predicted_price
        return "⚠️ 今天非交易日，且無過去預測數據"

    # 2️⃣ 檢查模型是否需要重新訓練
    today = datetime.date.today()
    last_training_date = None
    if os.path.exists(model_path):
        last_training_date = datetime.datetime.fromtimestamp(os.path.getmtime(model_path)).date()

    need_retrain = last_training_date is None or (today - last_training_date).days >= 1

    # 3️⃣ 取得最新股價數據
    stock = twstock.Stock(stock_code)
    start_year = today.year - 2
    data = []
    for year in range(start_year, today.year + 1):
        for month in range(1, 13):
            monthly_data = stock.fetch(year, month)
            if monthly_data:
                data.extend(monthly_data)

    if not data:
        return "⚠️ 無法取得股票數據，請檢查股票代碼是否正確。"

    df = pd.DataFrame(data, columns=['Date', 'capacity', 'turnover', 'open', 'high', 'low', 'close', 'change', 'transaction'])
    df.set_index('Date', inplace=True)

    # 4️⃣ 計算技術指標
    df['RSI'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    df['MACD'] = ta.trend.MACD(df['close']).macd()
    df['MACD_signal'] = ta.trend.MACD(df['close']).macd_signal()
    df['Bollinger_High'] = ta.volatility.BollingerBands(df['close']).bollinger_hband()
    df['Bollinger_Low'] = ta.volatility.BollingerBands(df['close']).bollinger_lband()

    df.dropna(inplace=True)

    # 5️⃣ 特徵選擇
    feature_columns = ['close', 'RSI', 'MACD', 'MACD_signal', 'Bollinger_High', 'Bollinger_Low']
    features = df[feature_columns].values

    # 正規化數據
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(features)

    # 設定時間步長 (過去 60 天預測下一天)
    time_step = 60
    X = [scaled_data[i - time_step:i, :] for i in range(time_step, len(scaled_data))]
    X = np.array(X)

    # 6️⃣ 如果模型已存在且數據是最新的，就直接載入模型
    if os.path.exists(model_path) and not need_retrain:
        model = load_model(model_path)
    else:
        # 重新訓練模型
        model = Sequential([
            Bidirectional(LSTM(128, return_sequences=True, input_shape=(X.shape[1], X.shape[2]))),
            Dropout(0.2),
            Bidirectional(LSTM(128, return_sequences=True)),
            Dropout(0.2),
            Bidirectional(LSTM(64, return_sequences=True)),
            Dropout(0.2),
            Bidirectional(LSTM(64, return_sequences=False)),
            Dropout(0.2),
            Dense(64, activation='relu'),
            Dense(1)
        ])

        model.compile(optimizer='adam', loss='mean_squared_error')
        model.fit(X, scaled_data[time_step:], epochs=10, batch_size=32)
        model.save(model_path)

    # 7️⃣ 預測未來一天的股價
    last_60_days = scaled_data[-time_step:].reshape(1, time_step, X.shape[2])
    predicted_price = model.predict(last_60_days)

    # 反標準化
    predicted_price = scaler.inverse_transform(
        np.hstack((predicted_price, np.zeros((1, features.shape[1] - 1))))
    )[0][0]

    # 存儲預測價格，假日時可以使用
    np.save(f"models/{stock_code}_last_pred.npy", predicted_price)

    return round(predicted_price, 2)