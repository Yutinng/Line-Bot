"""
當用戶輸入："地震" ,返回地震資訊
"""

import requests

def get_earthquake_info(token):
    result = []
    
    try:
        # 小區域地震資訊
        url = f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/E-A0016-001?Authorization={token}'
        response1 = requests.get(url)
        data1 = response1.json()
        eq1 = data1['records']['Earthquake'][0]
        t1 = eq1['EarthquakeInfo']['OriginTime']

        # 顯著有感地震資訊
        url2 = f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/E-A0015-001?Authorization={token}'
        response2 = requests.get(url2)
        data2 = response2.json()
        eq2 = data2['records']['Earthquake'][0]
        t2 = eq2['EarthquakeInfo']['OriginTime']

        # 選擇最新的地震資訊
        if t2 > t1:
            result = [eq2['ReportContent'], eq2['ReportImageURI']]
        else:
            result = [eq1['ReportContent'], eq1['ReportImageURI']]
    except Exception as e:
        print(f"❌ 取得地震資訊失敗: {e}")
        result = ['⚠️ 抓取地震資訊失敗...', '']
    
    return result
