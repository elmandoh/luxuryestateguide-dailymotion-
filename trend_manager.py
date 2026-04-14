from scraper import fetch_dailymotion_trends
from rss_generator import generate_rss

def start_process():
    print("1- 🎣 سحب التريندات...")
    if fetch_dailymotion_trends(limit=10):
        print("2- 📝 توليد ملف RSS...")
        if generate_rss():
            print("✅ تم تحديث dailymotion_feed.xml بنجاح!")
    else:
        print("❌ فشل السحب.")

if __name__ == "__main__":
    start_process()
