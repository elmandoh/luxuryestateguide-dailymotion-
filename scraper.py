import requests
import json

def fetch_dailymotion_trends(limit=10):
    # سحب الفيديوهات الأكثر زيارة مع العناوين والأوصاف
    url = f"https://api.dailymotion.com/videos?fields=title,description,views_total,url&sort=visited&limit={limit}"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        trends = []
        for item in data.get('list', []):
            trends.append({
                "title": item['title'],
                "views": item['views_total'],
                "desc": item['description'][:300], # سحب جزء من الوصف للتلخيص
                "url": item['url']
            })
            
        with open('trends_raw.json', 'w', encoding='utf-8') as f:
            json.dump(trends, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Error in Scraper: {e}")
        return False
