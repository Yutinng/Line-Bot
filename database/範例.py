import mysql.connector

#建立連線
connection = mysql.connector.connect(host='localhost',
                                     port='3307'
                                     user='root'
                                     password='@j23h36ajh4y',
                                     database = 'cat_dog')

# 開始使用
cursor = connection.cursor()

# 創建資料庫
# cursor.execute("create database `cat_dog`")   # 在()中寫sql指令




# 執行完指令要關閉
cursor.close()
# 有動到數據的要加：
cursor._connection.commit()  # 讓修改的指令提交出去生效

connection.close()