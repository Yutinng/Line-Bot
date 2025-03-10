"""各個常用的QuickReply選單"""

from linebot.v3.messaging import QuickReply, QuickReplyItem, PostbackAction


#　記帳功能的 QuickReply 選單
def expense_quickReply() -> QuickReply:
    return QuickReply(
        items=[
            QuickReplyItem(action=PostbackAction(label="查詢今日支出", data="查詢今日支出", display_text="我要查詢今日支出")),
            QuickReplyItem(action=PostbackAction(label="查詢本週支出", data="查詢本週支出", display_text="我要查詢本週支出")),
            QuickReplyItem(action=PostbackAction(label="查詢本月支出", data="查詢本月支出", display_text="我要查詢本月支出")),
            QuickReplyItem(action=PostbackAction(label="查詢本月收入", data="查詢本月收入", display_text="我要查詢本月收入")),
            QuickReplyItem(action=PostbackAction(label="設定月預算", data="設定月預算", display_text="我要設定月預算")),
            QuickReplyItem(action=PostbackAction(label="設定週預算", data="設定週預算", display_text="我要設定週預算"))
        ]
    )

# 股票功能的 QuickReply 選單
def stock_quickReply(stock_code: str, stock_name: str) -> QuickReply:
    return QuickReply(
        items=[
            QuickReplyItem(action=PostbackAction(label="⭐ 關注", data=f"watchlist,{stock_code},{stock_name}")),
            QuickReplyItem(action=PostbackAction(label="❌ 取消關注", data=f"unwatchlist,{stock_code},{stock_name}")),
            QuickReplyItem(action=PostbackAction(label="📰 相關新聞", data=f"news,{stock_code}")),
            QuickReplyItem(action=PostbackAction(label="📈 走勢圖", data=f"trend,{stock_code}")),
            QuickReplyItem(action=PostbackAction(label="📊 K 線圖", data=f"kchart,{stock_code}")),
            QuickReplyItem(action=PostbackAction(label="📌 查詢我的股票", data="查詢我的股票")),
            QuickReplyItem(action=PostbackAction(label="🔍 其他股票", data="search_new_stock")),
        ]
    )

# 照片風格轉換的 QuickReply 選單
def image_quickReply(image_path: str) -> QuickReply:
    return QuickReply(
        items=[
            QuickReplyItem(action=PostbackAction(label="✏️ 素描風格", data=f"filter,sketch,{image_path}")),
            QuickReplyItem(action=PostbackAction(label="🖼️ 浮雕效果", data=f"filter,emboss,{image_path}")),
            QuickReplyItem(action=PostbackAction(label="🖌️ 油畫風格", data=f"filter,oil_paint,{image_path}")),
            QuickReplyItem(action=PostbackAction(label="📽️ 黑白復古", data=f"filter,black_white,{image_path}")),
            QuickReplyItem(action=PostbackAction(label="✨ 霧面柔化", data=f"filter,soft_glow,{image_path}")),
            QuickReplyItem(action=PostbackAction(label="👀 大眼特效", data=f"filter,big_eyes,{image_path}")),
            QuickReplyItem(action=PostbackAction(label="🐱🐶品種辨識", data=f"breed_detect,{image_path}")) 
        ]
    )
