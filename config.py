from linebot.v3 import WebhookHandler
from linebot.v3.messaging import MessagingApi, Configuration


user_state = {}  # 共享用戶狀態，避免 Circular Import 問題


# 官方帳號資訊放置區：設定 Line Bot API 的 Access Token & Secret
ACCESS_TOKEN = '65nN+KPiWewuFsWcM6qeDxYvVlJAvUQo7sOtXFWsj7XZkmMSRq0TFzod+weRYuzXbQPr9eDtyD23VjAWgk6Nc9639NJRww/PTNeBrx4GhKIQnhlEZVuNVXmnbwV8sr+bFFpvsBKHSLoNULAlRBtnLAdB04t89/1O/w1cDnyilFU='
CHANNEL_SECRET = '2d5eaa1e69a05a761337495df4fedf2e'

# 建立 Line API 配置
handler = WebhookHandler(CHANNEL_SECRET)
configuration = Configuration(access_token=ACCESS_TOKEN)
line_bot_api = MessagingApi(configuration)
CWA_TOKEN = "CWA-A27AB7D0-2B62-4EEA-84DF-9CD035E693D6"


# MYSQL：
MYSQL_HOST = 'localhost'
MYSQL_PORT = '3307'
MYSQL_USER = 'root'
MYSQL_PASSWORD = '@j23h36ajh4y'
MYSQL_DATABASE = "expense_db"
