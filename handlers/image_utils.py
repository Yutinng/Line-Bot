"""照片風格轉換後刪除舊檔"""

import os
import glob

# 定義圖片存放路徑
transformed_images_path = "static/transformed_images"
os.makedirs(transformed_images_path, exist_ok=True)

def clear_old_images():
    """ 只保留最近 5 張轉換後的圖片，刪除更舊的 """
    image_files = sorted(
        glob.glob(os.path.join(transformed_images_path, "*.jpg")),  # 取得所有圖片
        key=os.path.getctime  # 依照建立時間排序（最舊的在最前面）
    )

    # 如果圖片數量超過 5 張，就刪掉較舊的
    if len(image_files) > 5:
        images_to_delete = image_files[:-5]  # 取最舊的 N-5 張
        print(f"🧹 發現 {len(image_files)} 張圖片，準備刪除 {len(images_to_delete)} 張較舊的圖片...")

        for file in images_to_delete:
            try:
                os.remove(file)
                print(f"🗑️ 已刪除 {file}")
            except Exception as e:
                print(f"❌ 無法刪除 {file}: {e}")
    else:
        print(f"✅ 目前圖片數量 ({len(image_files)}) 在限制範圍內，無需刪除。")
