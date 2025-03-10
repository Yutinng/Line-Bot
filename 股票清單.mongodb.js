// 使用 linebot 資料庫
use('linebot');

// 查詢 watchlist，看看目前有哪些關注的股票
db.watchlist.find().pretty();


//刪除watchlist中所有資料
db.watchlist.deleteMany({});

db.watchlist.countDocuments()