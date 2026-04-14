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

def get_latest_news():
    tree = ET.parse('dailymotion_feed.xml')
    root = tree.getroot()
    item = root.find('./channel/item')
    return item.find('title').text, item.find('description').text

def create_ai_script(title):
    client = Groq(api_key=GROQ_KEY)
    # طلبنا سكريبت من 15 كلمة فقط لضمان قصر المدة جداً
    prompt = f"اكتب جملة واحدة مشوقة جداً (15 كلمة فقط) عن: {title}"
    chat = client.chat.completions.create(
        model="llama-3.3-70b-versatile", 
        messages=[{"role": "user", "content": prompt}]
    )
    return chat.choices[0].message.content

def make_video(script):
    tts = gTTS(text=script, lang='ar')
    tts.save("audio.mp3")
    audio = AudioFileClip("audio.mp3")

    # تحديد مدة الفيديو بـ 10 ثواني كحد أقصى مهما كان طول الصوت
    final_duration = min(audio.duration, 10)
    audio = audio.subclip(0, final_duration)

    video = ColorClip(size=(720, 1280), color=(0, 0, 0)).set_duration(final_duration)
    video = video.set_audio(audio)
    
    video.write_videofile("output_video.mp4", fps=24, codec="libx264")
    return "output_video.mp4"

def upload_and_publish(filepath, title, desc):
    auth_data = {"grant_type": "password", "client_id": DM_KEY, "client_secret": DM_SECRET, "username": DM_USER, "password": DM_PASS, "scope": "manage_videos"}
    token = requests.post("https://api.dailymotion.com/oauth/token", data=auth_data).json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    upload_url = requests.get("https://api.dailymotion.com/file/upload", headers=headers).json().get("upload_url")
    with open(filepath, "rb") as f:
        video_url = requests.post(upload_url, files={"file": f}).json().get("url")
    
    publish_data = {"url": video_url, "title": title[:200], "description": desc[:500], "published": "true", "is_created_for_kids": "false"}
    res = requests.post("https://api.dailymotion.com/me/videos", data=publish_data, headers=headers).json()
    
    if 'id' in res:
        print(f"🚀 نجاح باهر! الفيديو نزل ID: {res['id']}")
    else:
        print(f"❌ لسه فيه مشكلة: {res}")

if __name__ == "__main__":
    t, d = get_latest_news()
    script = create_ai_script(t)
    v_path = make_video(script)
    upload_and_publish(v_path, t, script)
