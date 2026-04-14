import os
import requests
import xml.etree.ElementTree as ET
from groq import Groq
from gtts import gTTS
import moviepy as mp  # التغيير هنا
# إعداد المفاتيح من بيئة جيت هاب
GROQ_KEY = os.getenv("GROQ_API_KEY")
DM_KEY = os.getenv("DAILYMOTION_API_KEY")
DM_SECRET = os.getenv("DAILYMOTION_API_SECRET")
DM_USER = os.getenv("DM_USER")
DM_PASS = os.getenv("DM_PASS")

def run_process():
    try:
        # 1. قراءة الـ RSS
        tree = ET.parse('dailymotion_feed.xml')
        root = tree.getroot()
        item = root.find('./channel/item')
        title = item.find('title').text
        desc = item.find('description').text
        print(f"📌 تم سحب التريند: {title}")

        # 2. توليد سكريبت عبر Groq
        client = Groq(api_key=GROQ_KEY)
        prompt = f"اكتب سكريبت سريع لمقطع Reel عن موضوع: {title}. اجعل البداية قوية."
        chat = client.chat.completions.create(model="mixtral-8x7b-32768", messages=[{"role": "user", "content": prompt}])
        script = chat.choices[0].message.content
        print("🤖 تم توليد السكريبت بواسطة Groq")

        # 3. تحويل النص لصوت وصناعة فيديو بسيط
        tts = gTTS(text=script, lang='ar')
        tts.save("audio.mp3")
        audio = mp.AudioFileClip("audio.mp3")
        
        # إنشاء كليب أسود مدته نفس مدة الصوت
        video = mp.ColorClip(size=(720, 1280), color=(0, 0, 0)).set_duration(audio.duration)
        video = video.set_audio(audio)
        video.write_videofile("output_video.mp4", fps=24, codec="libx264")
        print("🎬 تم إنتاج الفيديو بنجاح")

        # 4. الرفع لديلى موشن
        auth_data = {
            "grant_type": "password",
            "client_id": DM_KEY,
            "client_secret": DM_SECRET,
            "username": DM_USER,
            "password": DM_PASS,
            "scope": "manage_videos"
        }
        token_res = requests.post("https://api.dailymotion.com/oauth/token", data=auth_data).json()
        token = token_res.get("access_token")
        
        headers = {"Authorization": f"Bearer {token}"}
        upload_url_res = requests.get("https://api.dailymotion.com/file/upload", headers=headers).json()
        upload_url = upload_url_res.get("upload_url")
        
        with open("output_video.mp4", "rb") as f:
            file_res = requests.post(upload_url, files={"file": f}).json()
            video_url = file_res.get("url")
        
        publish_data = {"url": video_url, "title": title, "description": script, "published": "true", "channel": "news"}
        final_res = requests.post("https://api.dailymotion.com/me/videos", data=publish_data, headers=headers).json()
        print(f"🚀 تم الرفع بنجاح! ID: {final_res.get('id')}")

    except Exception as e:
        print(f"❌ حدث خطأ: {e}")

if __name__ == "__main__":
    run_process()
