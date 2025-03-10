"""貓狗辨識，載入訓練好的貓狗辨識模型(利用ResNet50)"""

import os
import numpy as np
import tensorflow as tf
import json
import gdown
from tensorflow.keras.preprocessing import image
from tensorflow.keras.models import load_model

# 設定基礎路徑
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  
MODEL_PATH = os.path.join(BASE_DIR, "../dog_cat_breeds_resnet50v2.h5")
BREEDS_PATH = os.path.join(BASE_DIR, "breeds.npy")
TRANSLATION_PATH = os.path.join(BASE_DIR, "breeds_translation.json")

# Google Drive 模型下載 URL
GDRIVE_MODEL_ID = os.getenv("GDRIVE_MODEL_ID")
GDRIVE_URL = f"https://drive.google.com/uc?id={GDRIVE_MODEL_ID}"

# 確保模型檔案存在
if not os.path.exists(MODEL_PATH):
    print(f"⚠️ 模型檔案找不到！正在從 Google Drive 下載...")
    gdown.download(GDRIVE_URL, MODEL_PATH, quiet=False)
    print(f"✅ 下載完成！模型已儲存至：{MODEL_PATH}")
    
# 載入訓練好的模型
model = load_model(MODEL_PATH, compile=False)

# 載入品種名稱
try:
    BREEDS = np.load(BREEDS_PATH, allow_pickle=True).tolist()
    print(f"✅ 成功載入品種名稱，共 {len(BREEDS)} 種")
except FileNotFoundError:
    BREEDS = ["Unknown Breed"] * 143  
    print(f"⚠️ 找不到 breeds.npy，請確認檔案存在於：{BREEDS_PATH}")

# 載入品種翻譯名稱
try:
    with open(TRANSLATION_PATH, "r", encoding="utf-8") as f:
        BREEDS_TRANSLATION = json.load(f)
    print(f"✅ 成功載入品種翻譯，共 {len(BREEDS_TRANSLATION)} 種")
except FileNotFoundError:
    BREEDS_TRANSLATION = {}
    print(f"⚠️ 找不到 breeds_translation.json，請確認檔案存在於：{TRANSLATION_PATH}")

# 處理用戶傳來的圖片
def preprocess_image(img_path):
    """ 處理圖片，調整大小至 (224, 224) 並正規化 """
    img = image.load_img(img_path, target_size=(224, 224))  # 轉換大小
    img_array = image.img_to_array(img)  # 轉為數組
    img_array = np.expand_dims(img_array, axis=0)  # 增加批次維度
    img_array = img_array / 255.0  # 標準化
    return img_array

# 辨識品種
def predict_breed(img_path):
    """ 使用模型預測圖片中的貓狗品種，並返回中文與英文名稱 """
    img_array = preprocess_image(img_path)
    preds = model.predict(img_array)  # 取得預測結果
    breed_idx = np.argmax(preds)      # 找出最高機率的分類
    confidence = preds[0][breed_idx]  # 取得信心度

    # Debug: 查看模型輸出
    print(f"📌 模型輸出維度: {preds.shape}")
    print(f"📌 預測索引: {breed_idx}, 信心度: {confidence:.2f}")

    # 確保索引不會超出範圍
    if breed_idx >= len(BREEDS):
        breed_name = "Unknown Breed"
    else:
        breed_name = BREEDS[breed_idx]

    # 獲取中文品種名稱
    breed_name_cn = BREEDS_TRANSLATION.get(breed_name, "未知品種")

    return breed_name, breed_name_cn, confidence

# 測試
if __name__ == "__main__":
    test_img = os.path.join(BASE_DIR, "測試.jpg")  
    breed_en, breed_cn, confidence = predict_breed(test_img)
    print(f"預測品種: {breed_en} ({breed_cn})（信心度: {confidence:.2f}）")
