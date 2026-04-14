import os
import requests
import random
from groq import Groq
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip

# الإعدادات من GitHub Secrets
GROQ_KEY = os.getenv("GROQ_API_KEY")
PEXELS_KEY = os.getenv("PEXELS_API") # سنستخدم هذا الآن!
DM_KEY = os.getenv("DAILYMOTION_API_KEY")
DM_SECRET = os.getenv("DAILYMOTION_API_SECRET")
DM_USER = os.getenv("DM_USER")
DM_PASS = os.getenv("DM_PASS")

def get_pexels_image():
    """سحب صورة عقارات فاخرة من Pexels لتكون خلفية احترافية"""
    try:
        headers = {"Authorization": PEXELS_KEY}
        # البحث عن صور قصر فاخر
        url = "https://api.pexels.com/v1/search?query=luxury+mansion&per_page=20"
        res = requests.get(url, headers=headers).json()
        photo = random.choice(res['photos'])['src']['large2x']
        
        # تحميل الصورة
        img_data = requests.get(photo).content
        with open('background.jpg', 'wb') as f:
            f.write(img_data)
        return 'background.jpg'
    except Exception as e:
        print(f"❌ فشل سحب صورة من Pexels: {e}")
        return None

def create_ai_content():
    """توليد عنوان واسكريبت قصير جداً (لضمان قبول المدة) عبر Groq"""
    client = Groq(api_key=GROQ_KEY)
    # طلب عنوان واسكريبت (جملة واحدة قصيرة)
    prompt = "اكتب عنواناً جذاباً (7 كلمات) وجملة واحدة مشوقة جداً (10 كلمات) عن العقارات الفاخرة، باللغة العربية."
    chat = client.chat.completions.create(
        model="llama-3.3-70b-versatile", 
        messages=[{"role": "user", "content": prompt}]
    )
    content = chat.choices[0].message.content
    # تقسيم الرد للحصول على العنوان والاسكريبت بشكل تقريبي
    lines = content.strip().split('\n')
    title = lines[0][:150] if lines else "Luxury Real Estate Update"
    script = lines[-1] if len(lines) > 1 else content
    return title, script

def make_video(script):
    """تحويل الاسكريبت لفيديو Reels بصورة خلفية وصوت (المدة: 5-8 ثواني)"""
    tts = gTTS(text=script, lang='ar')
    tts.save("audio.mp3")
    audio = AudioFileClip("audio.mp3")
    # مدة قصيرة جداً (5-8 ثواني) لضمان قبول الحسابات الجديدة
    duration = min(audio.duration, 8) 
    
    # تحديد الخلفية (صورة من Pexels أو لون أسود كاحتياط)
    bg_path = get_pexels_image()
    if bg_path:
        clip = ImageClip(bg_path).set_duration(duration)
    else:
        from moviepy.editor import ColorClip
        clip = ColorClip(size=(720, 1280), color=(0,0,0)).set_duration(duration)
    
    # دمج الصوت والصورة
    video = clip.set_audio(audio.subclip(0, duration))
    output_file = "final_reel.mp4"
    # الحفاظ على الجودة والوزن الخفيف
    video.write_videofile(output_file, fps=24, codec="libx264")
    return output_file

def upload_and_publish(filepath, title, desc):
    """الرفع ومحاولة النشر كفيديو عام بالتصنيف المناسب"""
    # 1. الحصول على Access Token
    auth = {"grant_type": "password", "client_id": DM_KEY, "client_secret": DM_SECRET, "username": DM_USER, "password": DM_PASS, "scope": "manage_videos"}
    token = requests.post("https://api.dailymotion.com/oauth/token", data=auth).json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. الحصول على رابط الرفع
    up_url = requests.get("https://api.dailymotion.com/file/upload", headers=headers).json().get("upload_url")
    
    # 3. رفع ملف الفيديو
    with open(filepath, "rb") as f:
        v_url = requests.post(up_url, files={"file": f}).json().get("url")
    
    # 4. النشر كفيديو عام (published=true) ومع إضافة تصنيف (lifestyle)
    publish_data = {
        "url": v_url, 
        "title": title, 
        "description": desc, 
        "published": "true", # محاولة النشر كـ Public
        "channel": "lifestyle", # إضافة تصنيف قد يساعد في النشر
        "is_created_for_kids": "false"
    }
    
    res = requests.post("https://api.dailymotion.com/me/videos", data=publish_data, headers=headers).json()
    
    if 'id' in res:
        print(f"✅ تم الرفع بنجاح! ID الفيديو هو: {res['id']}")
        print(f"🔗 رابط الفيديو: https://www.dailymotion.com/video/{res['id']}")
    else:
        print(f"🛑 فشل النشر التلقائي كـ Public. الرد من السيرفر: {res}")

if __name__ == "__main__":
    print("🚀 بدء عملية إنتاج الـ Reel...")
    # 1. توليد المحتوى
    title, script = create_ai_content()
    print(f"📝 العنوان: {title}")
    
    # 2. صناعة الفيديو
    v_path = make_video(script)
    
    # 3. الرفع والنشر
    upload_and_publish(v_path, title, script)
