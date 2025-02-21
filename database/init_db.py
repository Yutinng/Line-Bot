import sys
import os

# 手動添加 AI_LINE_BOT 根目錄到 Python 模組路徑
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


import mysql.connector
from config import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD  # 直接從 config.py 導入 MySQL 參數

# 建立 MySQL 資料庫：expense_db
MYSQL_DATABASE = "expense_db"

def create_database():
    """ 連接 MySQL 並建立資料庫（如果不存在） """
    connection = mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD
    )
    cursor = connection.cursor()

    # 建立資料庫（如果不存在）
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}`")
    print(f"✅ 資料庫 `{MYSQL_DATABASE}` 已建立或已存在")

    cursor.close()
    connection.close()

# 建立表格：expenses
def create_expenses_table():
    """ 連接 MySQL 並建立 expenses 表（如果不存在） """
    connection = mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE  # 指定剛剛建立的資料庫
    )
    cursor = connection.cursor()

    # 建立記帳表格（如果不存在）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            `id` INT AUTO_INCREMENT PRIMARY KEY,  
            `date` DATETIME DEFAULT CURRENT_TIMESTAMP,
            `category` VARCHAR(50),
            `amount` DECIMAL(10,2),
            `user_id` VARCHAR(50)
        )
    """)
    print("✅ `expenses` 表已建立或已存在")

    connection.commit()
    cursor.close()
    connection.close()

if __name__ == "__main__":
    create_database()  # 先建立資料庫
    create_expenses_table()  # 再建立表格
    print("🎉 MySQL 資料庫與表格初始化完成！")
