"""
當用戶輸入："天氣" 或直接傳送位置資訊時，
利用中央氣象局API獲取天氣預報及空氣品質返回給用戶，
並根據溫度、空氣品質給用戶一些貼心提醒
"""
import os
import requests
import json

CWA_TOKEN = os.getenv('CWA_TOKEN')
MOENV_API_KEY = os.getenv('MOENV_API_KEY')

def get_weather_info(address):
    result = "⚠️ 找不到該地點的氣象資料"
    advice = ""
    
    # 1.即時天氣 API
    url_realtime = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0001-001?Authorization={CWA_TOKEN}"
    
    try:
        req = requests.get(url_realtime)
        data = req.json()

        if "records" in data and "Station" in data["records"]:
            for station in data["records"]["Station"]:
                city = station["GeoInfo"]["CountyName"]
                town = station["GeoInfo"]["TownName"]
                weather = station["WeatherElement"]["Weather"]
                temp = station["WeatherElement"]["AirTemperature"]
                humidity = station["WeatherElement"]["RelativeHumidity"]
                
                if city in address or town in address:
                    result = f"📍「{address}」目前天氣狀況「{weather}」，溫度 {temp}°C，相對濕度 {humidity}%！"
                    
                    # 貼心提醒
                    if temp >= 35:
                        advice += "🔥Warning！高溫警報！別離開冷氣房！\n"
                    elif 30 <= temp < 35:
                        advice += "🌞今天超熱，記得防曬並多喝水。\n"
                    elif 10 < temp <= 20:
                        advice = "🧥今天有點冷，記得穿暖一點歐！"
                    elif temp <= 10:
                        advice += "❄️要凍僵啦，請裹好棉被！\n"
                    
                    # 提醒帶傘
                    if any(r in weather for r in ["雨", "雷陣雨", "陰天有雨", "毛毛雨"]):
                        advice += "可能會下雨，建議攜帶雨具，以防變成落湯雞！\n"
                    break

    except Exception as e:
        print(f"❌ 即時天氣 API 錯誤: {e}")
        result = "⚠️ 取得即時天氣資訊時發生錯誤"

    # 2.空氣品質 API
    try:
        url_aqi = f"https://data.moenv.gov.tw/api/v2/aqx_p_432?api_key={MOENV_API_KEY}&limit=1000&sort=ImportDate desc&format=JSON"
        req_aqi = requests.get(url_aqi)
        data_aqi = req_aqi.json()

        if "records" in data_aqi:
            for record in data_aqi["records"]:
                if record["county"] in address:
                    aqi = int(record["aqi"])
                    status = record["status"]
                    result += f"\n\n🌫 AQI：{aqi}，空氣品質 {status}。"
                    
                    # 空氣品質提醒
                    if aqi >= 100:
                        advice += "💨空氣品質較差，外建議出戴個口罩！\n"
                    break
    except Exception as e:
        print(f"❌ 空氣品質 API 錯誤: {e}")
        result += "\n⚠️ 無法取得空氣品質資訊"
    
    # 添加貼心提醒
    if advice:
        result += f"\n_________________\n💡 貼心提醒：\n{advice}"
    
    return result
