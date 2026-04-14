import os
import requests
import xml.etree.ElementTree as ET
from groq import Groq
from gtts import gTTS
from moviepy.editor import ColorClip, AudioFileClip

GROQ_KEY = os.getenv("GROQ_API_KEY")
DM_KEY = os.getenv("DAILYMOTION_API_KEY")
DM_SECRET = os.getenv("DAILYMOTION_API_SECRET")
DM_USER = os.getenv("DM_USER")
DM_PASS = os.getenv("DM_PASS")

def create_ai_script():
    client = Groq(api_key=GROQ_KEY)
    # طلب سكريبت من 5 كلمات فقط لضمان مدة لا تتعدى 5 ثواني
    prompt = "اكتب 5 كلمات فقط مشوقة عن العقارات."
    chat = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
    return chat.choices[0].message.content

def make_video(script):
    tts = gTTS(text=script, lang='ar')
    tts.save("audio.mp3")
    audio = AudioFileClip("audio.mp3")
    
    # تحديد مدة الفيديو بـ 5 ثواني فقط كحد أقصى (أمان تام)
    final_duration = min(audio.duration, 5)
    audio = audio.subclip(0, final_duration)

    # تقليل الحجم لضمان سرعة الرفع والقبول
    video = ColorClip(size=(640, 360), color=(0, 0, 0)).set_duration(final_duration)
    video = video.set_audio(audio)
    
    output_file = "output_video.mp4"
    # استخدام بروفايل سريع جداً وأقل جودة للقبول
    video.write_videofile(output_file, fps=20, codec="libx264", audio_codec="aac")
    return output_file

def upload_and_publish(filepath):
    auth_data = {"grant_type": "password", "client_id": DM_KEY, "client_secret": DM_SECRET, "username": DM_USER, "password": DM_PASS, "scope": "manage_videos"}
    token = requests.post("https://api.dailymotion.com/oauth/token", data=auth_data).json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    upload_url = requests.get("https://api.dailymotion.com/file/upload", headers=headers).json().get("upload_url")
    with open(filepath, "rb") as f:
        video_url = requests.post(upload_url, files={"file": f}).json().get("url")
    
    # نشر بأقل قدر من البيانات لتجنب أي رفض
    publish_data = {"url": video_url, "title": "Quick Update", "published": "true"}
    res = requests.post("https://api.dailymotion.com/me/videos", data=publish_data, headers=headers).json()
    
    if 'id' in res:
        print(f"✅ أخيراً! تم القبول بـ ID: {res['id']}")
    else:
        print(f"❌ الرد من السيرفر: {res}")

if __name__ == "__main__":
    script = create_ai_script()
    v_path = make_video(script)
    upload_and_publish(v_path)
