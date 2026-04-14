import os
import requests
import random
from groq import Groq
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip

# الإعدادات
GROQ_KEY = os.getenv("GROQ_API_KEY")
PEXELS_KEY = os.getenv("PEXELS_API")
DM_KEY = os.getenv("DAILYMOTION_API_KEY")
DM_SECRET = os.getenv("DAILYMOTION_API_SECRET")
DM_USER = os.getenv("DM_USER")
DM_PASS = os.getenv("DM_PASS")

def get_pexels_image():
    """سحب صورة عقارات فاخرة من Pexels"""
    try:
        headers = {"Authorization": PEXELS_KEY}
        url = "https://api.pexels.com/v1/search?query=luxury+mansion&per_page=15"
        res = requests.get(url, headers=headers).json()
        photo = random.choice(res['photos'])['src']['large2x']
        img_data = requests.get(photo).content
        with open('bg.jpg', 'wb') as f:
            f.write(img_data)
        return 'bg.jpg'
    except:
        return None

def create_ai_script():
    client = Groq(api_key=GROQ_KEY)
    prompt = "اكتب جملة واحدة جذابة جداً عن القصور الفاخرة (7 كلمات فقط)."
    chat = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
    return chat.choices[0].message.content

def make_video(script):
    # الصوت
    tts = gTTS(text=script, lang='ar')
    tts.save("audio.mp3")
    audio = AudioFileClip("audio.mp3")
    duration = min(audio.duration, 7) # مدة قصيرة للقبول
    
    # الخلفية (صورة من Pexels أو لون أسود كاحتياط)
    bg_path = get_pexels_image()
    if bg_path:
        clip = ImageClip(bg_path).set_duration(duration)
    else:
        from moviepy.editor import ColorClip
        clip = ColorClip(size=(720, 1280), color=(0,0,0)).set_duration(duration)
    
    video = clip.set_audio(audio.subclip(0, duration))
    video.write_videofile("output.mp4", fps=24, codec="libx264")
    return "output.mp4"

def upload(filepath, title):
    # كود الرفع الذي نجحنا فيه سابقاً
    auth = {"grant_type": "password", "client_id": DM_KEY, "client_secret": DM_SECRET, "username": DM_USER, "password": DM_PASS, "scope": "manage_videos"}
    token = requests.post("https://api.dailymotion.com/oauth/token", data=auth).json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    up_url = requests.get("https://api.dailymotion.com/file/upload", headers=headers).json().get("upload_url")
    v_url = requests.post(up_url, files={"file": open(filepath, "rb")}).json().get("url")
    
    res = requests.post("https://api.dailymotion.com/me/videos", data={"url": v_url, "title": title, "published": "true"}, headers=headers).json()
    print(f"✅ تم الرفع بنجاح! ID: {res.get('id')}")

if __name__ == "__main__":
    script = create_ai_script()
    path = make_video(script)
    upload(path, script)
