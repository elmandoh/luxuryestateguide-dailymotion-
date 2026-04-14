from scraper import fetch_dailymotion_trends
from summarizer import generate_reels_scripts

def start_process():
    print("Step 1: 🎣 سحب التريندات من ديلى موشن...")
    if fetch_dailymotion_trends(limit=5):
        print("✅ تم سحب البيانات بنجاح.")
        
        print("Step 2: 🤖 توليد سكريبتات الـ Reels بالذكاء الاصطناعي...")
        if generate_reels_scripts():
            print("✅ تم إنتاج السكريبتات وحفظها في reels_scripts.json")
        else:
            print("❌ فشل جزء الذكاء الاصطناعي.")
    else:
        print("❌ فشل سحب البيانات.")

if __name__ == "__main__":
    start_process()
