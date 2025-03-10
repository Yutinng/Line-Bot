"""
用戶傳送照片,利用QuickReply選擇要轉換的風格效果
"""
import cv2
import numpy as np
import mediapipe as mp

mp_face_mesh = mp.solutions.face_mesh

def sketch_effect(img):
    """ 素描風格（黑白鉛筆畫） """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    invert = cv2.bitwise_not(gray)
    blur = cv2.GaussianBlur(invert, (21, 21), 0)
    inverted_blur = cv2.bitwise_not(blur)
    sketch = cv2.divide(gray, inverted_blur, scale=256.0)
    return sketch

def emboss_effect(img):
    """ 浮雕效果 """
    kernel = np.array([[ -2, -1,  0],
                       [ -1,  1,  1],
                       [  0,  1,  2]])
    embossed = cv2.filter2D(img, -1, kernel)
    return embossed

def oilPaint_effect(img):
    """ 油畫風格 """
    oil_paint = cv2.xphoto.oilPainting(img, 7, 1)
    return oil_paint

def blackWhite_effect(image):
    """ 黑白復古風格 """
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

def softGlow_effect(image, blur_ksize=55, alpha=0.5, beta=0.5, gamma=2, softness=0.8):
    """ 霧面 """
    image = image.astype(np.float32) / 255.0
    blurred1 = cv2.GaussianBlur(image, (blur_ksize, blur_ksize), 0)
    blurred2 = cv2.GaussianBlur(blurred1, (blur_ksize, blur_ksize), 0)
    soft_glow = cv2.addWeighted(image, alpha, blurred2, beta, gamma / 255.0)
    glow_layer = cv2.GaussianBlur(soft_glow, (21, 21), 10)
    soft_glow = cv2.addWeighted(soft_glow, 1 - softness, glow_layer, softness, 0)
    soft_glow = (soft_glow * 255).clip(0, 255).astype(np.uint8)
    return soft_glow

def bigEyes_effect(img, scale=1.6):
    """大眼特效"""
    with mp_face_mesh.FaceMesh(static_image_mode=True,
                               refine_landmarks=True,
                               max_num_faces=1,
                               min_detection_confidence=0.5) as face_mesh:
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb_img)

        if not results.multi_face_landmarks:
            print("❌ 未偵測到人臉，無法進行眼睛放大")
            return img

        ih, iw, _ = img.shape
        face_landmarks = results.multi_face_landmarks[0]

        # 定義左右眼的座標 (以眼睛中心位置計算)
        left_eye_idxs = [33, 133, 159, 145]
        right_eye_idxs = [362, 263, 386, 374]

        # 計算眼睛中心點
        def get_eye_center(eye_idxs):
            x = np.mean([face_landmarks.landmark[i].x for i in eye_idxs]) * iw
            y = np.mean([face_landmarks.landmark[i].y for i in eye_idxs]) * ih
            return int(x), int(y)

        left_eye_center = get_eye_center(left_eye_idxs)
        right_eye_center = get_eye_center(right_eye_idxs)

        # 計算眼睛區域半徑
        def get_eye_radius(eye_idxs):
            eye_points = [(face_landmarks.landmark[i].x * iw,
                           face_landmarks.landmark[i].y * ih) for i in eye_idxs]
            eye_radius = int(max([np.linalg.norm(np.array(p) - np.array(get_eye_center(eye_idxs)))
                                  for p in eye_points]) * scale)
            return eye_radius

        left_eye_radius = get_eye_radius(left_eye_idxs)
        right_eye_radius = get_eye_radius(right_eye_idxs)

        # 影像複製，避免修改原圖
        output_img = img.copy()

        # 眼睛放大函數（自然邊緣融合）
        def enlarge_eye(image, eye_center, eye_radius, scale_factor):
            mask = np.zeros(image.shape[:2], dtype=np.uint8)
            cv2.circle(mask, eye_center, eye_radius, 255, -1)

            # 提取眼睛區域
            eye_region = cv2.bitwise_and(image, image, mask=mask)

            # 擷取眼睛區域做放大處理
            x1, y1 = eye_center[0] - eye_radius, eye_center[1] - eye_radius
            x2, y2 = eye_center[0] + eye_radius, eye_center[1] + eye_radius

            # 確保座標邊界正確
            x1, y1, x2, y2 = max(0, x1), max(0, y1), min(iw, x2), min(ih, y2)

            eye_crop = eye_region[y1:y2, x1:x2]
            enlarged_eye = cv2.resize(eye_crop, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_LINEAR)

            eh, ew = enlarged_eye.shape[:2]

            # 計算放大後放置位置
            ex1 = max(eye_center[0] - ew // 2, 0)
            ey1 = max(eye_center[1] - eh // 2, 0)
            ex2 = min(ex1 + ew, iw)
            ey2 = min(ey1 + eh, ih)

            # 建立放大後的眼睛遮罩
            eye_gray = cv2.cvtColor(enlarged_eye, cv2.COLOR_BGR2GRAY)
            _, eye_mask = cv2.threshold(eye_gray, 1, 255, cv2.THRESH_BINARY)

            # 邊緣平滑融合
            eye_area = output_img[ey1:ey2, ex1:ex2]
            eye_area_no_eye = cv2.bitwise_and(eye_area, eye_area, mask=cv2.bitwise_not(eye_mask))
            final_eye_area = cv2.add(eye_area_no_eye, enlarged_eye[:ey2-ey1, :ex2-ex1])

            # 將處理後的眼睛區域放回原圖
            output_img[ey1:ey2, ex1:ex2] = final_eye_area

        # 分別處理左右眼
        enlarge_eye(output_img, left_eye_center, left_eye_radius, scale_factor=scale)
        enlarge_eye(output_img, right_eye_center, right_eye_radius, scale_factor=scale)

        return output_img


def resize_and_show(title, img, max_size=500):
    """ 縮小圖片，確保完整顯示，並設定視窗大小 """
    h, w = img.shape[:2]

    # 計算縮放比例
    scale = max_size / max(h, w)  # 根據長邊計算縮放比例
    new_w, new_h = int(w * scale), int(h * scale)

    resized_img = cv2.resize(img, (new_w, new_h))  # 重新調整大小

    # 設定視窗大小，避免全螢幕
    cv2.namedWindow(title, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(title, new_w, new_h)  # 設定視窗大小
    cv2.imshow(title, resized_img)

# 測試  
if __name__ == "__main__":
    img = cv2.imread("static/richmenu.jpg")

    if img is None:
        print("❌ 讀取圖片失敗，請確認圖片檔案是否存在！")
    else:
        sketch_result = sketch_effect(img)
        emboss_result = emboss_effect(img)
        oil_paint_result = oilPaint_effect(img)
        black_white_result = blackWhite_effect(img)
        soft_glow_result = softGlow_effect(img)
        big_eyes_result = bigEyes_effect(img, scale=1.6)

        resize_and_show("Original Image", img)
        resize_and_show("Sketch Effect", sketch_result)
        resize_and_show("Emboss Effect", emboss_result)
        resize_and_show("Oil Paint Effect", oil_paint_result)
        resize_and_show("Black & White Effect", black_white_result)
        resize_and_show("Soft Glow Effect", soft_glow_result)
        resize_and_show("Big Eyes Effect", big_eyes_result)

        cv2.waitKey(0)
        cv2.destroyAllWindows()
