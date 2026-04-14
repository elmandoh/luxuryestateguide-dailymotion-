import requests
import json

def fetch_dailymotion_trends(limit=10):
    """يسحب الفيديوهات الأكثر مشاهدة حالياً على المنصة"""
    # التصفية: الأكثر زيارة (visited) + الفيديوهات المميزة (featured)
    url = f"https://api.dailymotion.com/videos?fields=id,title,description,tags,views_total,url&sort=visited&limit={limit}"
    
    try:
        response = requests.get(url)
        response.raise_for_status() # التأكد أن الطلب نجح
        data = response.json()
        
        # تحويل البيانات لشكل منظم (List of Dictionaries)
        trends = []
        for item in data.get('list', []):
            video_info = {
                "title": item['title'],
                "views": item['views_total'],
                "desc": item['description'][:200] + "...", # سحب أول 200 حرف من الوصف للتلخيص
                "tags": item.get('tags', []),
                "url": item['url']
            }
            trends.append(video_info)
            
        # حفظ النتائج في ملف JSON لاستخدامه لاحقاً
        with open('trends_data.json', 'w', encoding='utf-8') as f:
            json.dump(trends, f, ensure_ascii=False, indent=4)
            
        print(f"✅ تم سحب {len(trends)} فيديوهات بنجاح وحفظها في trends_data.json")
        return True
    except Exception as e:
        print(f"❌ فشل السحب: {e}")
        return False

if __name__ == "__main__":
    fetch_dailymotion_trends()
