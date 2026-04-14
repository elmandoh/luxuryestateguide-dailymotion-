import os
import requests
import xml.etree.ElementTree as ET
from groq import Groq
from gtts import gTTS
import moviepy.editor as mp

# إعداد المفاتيح من GitHub Secrets
GROQ_KEY = os.getenv("GROQ_API_KEY")
DM_KEY = os.getenv("DAILYMOTION_API_KEY")
DM_SECRET = os.getenv("DAILYMOTION_API_SECRET")
DM_USER = os.getenv("DM_USER")
DM_PASS = os.getenv("DM_PASS")

def get_latest_news():
    tree = ET.parse('dailymotion_feed.xml')
    root = tree.getroot()
    item = root.find('./channel/item')
    return item.find('title').text, item.find('description').text

def create_ai_script(title, desc):
    client = Groq(api_key=GROQ_KEY)
    prompt = f"اكتب سكريبت فيديو قصير (Reel) جذاب جداً عن: {title}. الوصف: {desc}. اجعل الكلام مشوقاً وباللهجة العربية البيضاء."
    chat = client.chat.completions.create(model="mixtral-8x7b-32768", messages=[{"role": "user", "content": prompt}])
    return chat.choices[0].message.content

def make_video(script):
    # 1. تحويل النص لصوت
    tts = gTTS(text=script, lang='ar')
    tts.save("audio.mp3")
    audio = mp.AudioFileClip("audio.mp3")

    # 2. إنشاء الفيديو (خلفية سوداء مع نص بسيط)
    # يمكنك وضع صورة خلفية باسم background.jpg لو أردت
    video = mp.ColorClip(size=(720, 1280), color=(0, 0, 0), duration=audio.duration)
    video = video.set_audio(audio)
    
    video.write_videofile("final_video.mp4", fps=24, codec="libx264")
    return "final_video.mp4"

def upload_to_dm(filepath, title, desc):
    # الحصول على Token
    auth_data = {
        "grant_type": "password",
        "client_id": DM_KEY,
        "client_secret": DM_SECRET,
        "username": DM_USER,
        "password": DM_PASS,
        "scope": "manage_videos"
    }
    r = requests.post("https://api.dailymotion.com/oauth/token", data=auth_data).json()
    token = r.get("access_token")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # طلب رابط الرفع
    url_res = requests.get("https://api.dailymotion.com/file/upload", headers=headers).json()
    upload_url = url_res.get("upload_url")
    
    # رفع الملف
    with open(filepath, "rb") as f:
        file_res = requests.post(upload_url, files={"file": f}).json()
        video_url = file_res.get("url")
    
    # النشر
    publish_data = {"url": video_url, "title": title, "description": desc, "published": "true", "channel": "news"}
    requests.post("https://api.dailymotion.com/me/videos", data=publish_data, headers=headers)
    print("🚀 تم الرفع بنجاح!")

if __name__ == "__main__":
    t, d = get_latest_news()
    s = create_ai_script(t, d)
    video_path = make_video(s)
    upload_to_dm(video_path, t, s)
