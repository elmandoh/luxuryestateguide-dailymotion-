import os
import requests
import xml.etree.ElementTree as ET
from groq import Groq
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, TextClip, CompositeVideoClip

# 1. سحب البيانات من الـ RSS اللي إنت عملته
def get_latest_trend():
    tree = ET.parse('dailymotion_feed.xml')
    root = tree.getroot()
    item = root.find('./channel/item') # هناخد أول فيديو (الأحدث)
    return item.find('title').text, item.find('description').text

# 2. تلخيص المحتوى باستخدام Groq
def create_script(title, desc):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    prompt = f"اكتب سكريبت فيديو قصير جداً (30 ثانية) عن: {title}. الوصف: {desc}. استخدم لغة عربية بسيطة ومثيرة."
    completion = client.chat.completions.create(model="mixtral-8x7b-32768", messages=[{"role": "user", "content": prompt}])
    return completion.choices[0].message.content

# 3. صناعة الفيديو (The Magic)
def build_video(script, output_name="final_reels.mp4"):
    # تحويل النص لصوت
    tts = gTTS(script, lang='ar')
    tts.save("voice.mp3")
    
    # إنشاء فيديو بسيط (خلفية سوداء أو صورة مع نص)
    audio = AudioFileClip("voice.mp3")
    # بنعمل فيديو مدته نفس مدة الصوت
    clip = ImageClip("background.jpg").set_duration(audio.duration) 
    video = clip.set_audio(audio)
    
    video.write_videofile(output_name, fps=24)
    return output_name

# 4. الرفع لـ Dailymotion
def upload_to_dailymotion(file_path, title):
    # هنا هنستخدم الـ Access Token بتاعك لرفع الفيديو
    # (محتاجين نجهز الـ API Credentials في خطوة تانية)
    print(f"Uploading {title} to Dailymotion...")
