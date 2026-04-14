import os
import requests
import random
import xml.etree.ElementTree as ET
from groq import Groq
from gtts import gTTS
from moviepy.editor import ColorClip, AudioFileClip

# إعداد المفاتيح من GitHub Secrets
GROQ_KEY = os.getenv("GROQ_API_KEY")
DM_KEY = os.getenv("DAILYMOTION_API_KEY")
DM_SECRET = os.getenv("DAILYMOTION_API_SECRET")
DM_USER = os.getenv("DM_USER")
DM_PASS = os.getenv("DM_PASS")

def get_latest_news():
    """سحب أحدث خبر من ملف الـ RSS المحفوظ"""
    try:
        tree = ET.parse('dailymotion_feed.xml')
        root = tree.getroot()
        item = root.find('./channel/item')
        return item.find('title').text, item.find('description').text
    except Exception as e:
        print(f"❌ خطأ في قراءة الـ RSS: {e}")
        return "New Trend", "No description available"

def create_ai_script(title, desc):
    """توليد سكريبت قصير جداً عبر Groq لضمان عدم تخطي مدة الفيديو"""
    try:
        client = Groq(api_key=GROQ_KEY)
        # طلب سكريبت قصير جداً (أقل من 30 كلمة) لتجنب رفض ديلى موشن للمدة الطويلة
        prompt = f"اكتب سكريبت سريع جداً لمقطع Reel لا يتجاوز 30 كلمة عن: {title}. اجعل الكلام مشوقاً وباللهجة العربية البيضاء."
        chat = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=[{"role": "user", "content": prompt}]
        )
        return chat.choices[0].message.content
    except Exception as e:
        print(f"❌ خطأ في Groq: {e}")
        return f"تحقق من هذا الخبر الجديد: {title}"

def make_video(script):
    """تحويل السكريبت لفيديو (Reel) بصوت وقص المدة تلقائياً"""
    try:
        # 1. تحويل النص لصوت
        tts = gTTS(text=script, lang='ar')
        tts.save("audio.mp3")
        audio = AudioFileClip("audio.mp3")

        # 2. قص الصوت لو زاد عن 20 ثانية (أمان إضافي لديلى موشن)
        if audio.duration > 20:
            audio = audio.subclip(0, 20)

        # 3. إنشاء فيديو (خلفية سوداء حالياً) بنفس مدة الصوت
        video = ColorClip(size=(720, 1280), color=(0, 0, 0)).set_duration(audio.duration)
        video = video.set_audio(audio)
        
        output_file = "output_video.mp4"
        video.write_videofile(output_file, fps=24, codec="libx264")
        return output_file
    except Exception as e:
        print(f"❌ خطأ في صناعة الفيديو: {e}")
        return None

def upload_and_publish(filepath, title, desc):
    """الرفع والنشر النهائي على ديلى موشن مع معالجة أخطاء البراميترز"""
    try:
        # 1. الحصول على Access Token
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
        
        # 2. طلب رابط الرفع
        url_res = requests.get("https://api.dailymotion.com/file/upload", headers=headers).json()
        upload_url = url_res.get("upload_url")
        
        # 3. رفع ملف الفيديو
        with open(filepath, "rb") as f:
            file_res = requests.post(upload_url, files={"file": f}).json()
            video_url = file_res.get("url")
        
        # 4. النشر (تم حذف 'channel' لتجنب أخطاء التصنيف)
        publish_data = {
            "url": video_url,
            "title": title[:250],
            "description": desc[:900],
            "published": "true",
            "is_created_for_kids": "false"
        }
        
        final_res = requests.post("https://api.dailymotion.com/me/videos", data=publish_data, headers=headers).json()
        
        if 'id' in final_res:
            print(f"🚀 تم الرفع والنشر بنجاح! ID: {final_res.get('id')}")
        else:
            print(f"❌ فشل النشر. الرد: {final_res}")

    except Exception as e:
        print(f"❌ خطأ في الرفع: {e}")

if __name__ == "__main__":
    print("🎬 بدء عملية إنتاج الفيديو...")
    t, d = get_latest_news()
    s = create_ai_script(t, d)
    video_path = make_video(s)
    
    if video_path:
        upload_and_publish(video_path, t, s)
    else:
        print("🛑 توقفت العملية بسبب فشل إنتاج الفيديو.")
