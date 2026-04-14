import os
import requests
import xml.etree.ElementTree as ET
from groq import Groq

# إعدادات Groq وديلى موشن
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def get_data_from_rss():
    # قراءة ملف الـ RSS اللي الأكشن التاني عمله
    tree = ET.parse('dailymotion_feed.xml')
    root = tree.getroot()
    items = []
    for item in root.findall('./channel/item'):
        items.append({
            'title': item.find('title').text,
            'desc': item.find('description').text
        })
    return items

def summarize_with_groq(text):
    completion = groq_client.chat.completions.create(
        model="mixtral-8x7b-32768", # موديل سريع وممتاز
        messages=[{"role": "user", "content": f"حول النص التالي لسكريبت فيديو قصير وجذاب باللغة العربية (Short Reel): {text}"}],
    )
    return completion.choices[0].message.content

def run_video_task():
    videos_data = get_data_from_rss()
    for vid in videos_data[:3]:  # هنجرب في أول 3 فيديوهات بس
        print(f"Processing: {vid['title']}")
        script = summarize_with_groq(vid['desc'])
        print(f"Generated Script: {script}")
        
        # هنا بتيجي مرحلة الـ Video Generation (محتاجة مكتبات زي MoviePy)
        # ومرحلة الـ Upload لـ Dailymotion
        
if __name__ == "__main__":
    run_video_task()
