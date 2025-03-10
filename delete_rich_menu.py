"""
刪除所有已建立的 Rich Menu
"""
import os
import requests

ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')

# 設定 API 請求標頭
headers = {
    'Authorization': f'Bearer {ACCESS_TOKEN}',
    'Content-Type': 'application/json'
}

def delete_all_rich_menus():
    # 取得所有 Rich Menu
    url = "https://api.line.me/v2/bot/richmenu/list"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"❌ 無法取得 Rich Menu 列表，錯誤代碼: {response.status_code}")
        print(response.text)
        return

    rich_menus = response.json().get("richmenus", [])
    if not rich_menus:
        print("❌ 沒有可刪除的 Rich Menu")
        return

    # 刪除每個 Rich Menu
    for rich_menu in rich_menus:
        rich_menu_id = rich_menu["richMenuId"]
        delete_url = f"https://api.line.me/v2/bot/richmenu/{rich_menu_id}"
        delete_response = requests.delete(delete_url, headers=headers)

        if delete_response.status_code == 200:
            print(f"✅ 成功刪除 Rich Menu: {rich_menu_id}")
        else:
            print(f"❌ 刪除失敗: {rich_menu_id}, 錯誤代碼: {delete_response.status_code}")
            print(delete_response.text)

if __name__ == "__main__":
    delete_all_rich_menus()
