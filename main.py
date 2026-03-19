import feedparser, asyncio, edge_tts, requests, os, re
import moviepy.editor as mp  # استدعاء بديل وأكثر استقراراً
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
from requests_toolbelt import MultipartEncoder

# 1. إعدادات المفاتيح (تأكد أنها في GitHub Secrets)
PEXELS_API = os.getenv("PEXELS_API")
DM_KEY = os.getenv("DM_API_KEY")
DM_SECRET = os.getenv("DM_API_SECRET")
DM_USER = os.getenv("DM_USER")
DM_PASS = os.getenv("DM_PASS")
BLOG_FEED = "https://luxuryestateguide.blogspot.com/feeds/posts/default"

def clean_html(raw_html):
    """تنظيف نص المقال من أكواد HTML ليكون صالحاً للقراءة"""
    cleanr = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')
    return re.sub(cleanr, '', raw_html)

async def main():
    print("🔍 Checking for new posts...")
    feed = feedparser.parse(BLOG_FEED)
    if not feed.entries:
        print("❌ No posts found in feed.")
        return
    
    post = feed.entries[0]
    title = post.title
    link = post.link
    
    # التحقق من الذاكرة (منع التكرار)
    if os.path.exists("last_post.txt"):
        with open("last_post.txt", "r") as f:
            if f.read().strip() == title:
                print(f"⚠️ Skipping: '{title}' is already published.")
                return

    print(f"🌟 New Post Detected: {title}")

    # --- 2. تجهيز النص الكامل (العنوان + المحتوى) ---
    content_text = clean_html(post.content[0].value)
    full_narrative = f"{title}. {content_text}"
    # تحديد الحد الأقصى للحروف لضمان استقرار العملية (حوالي 3-5 دقائق فيديو)
    full_narrative = full_narrative[:2500] 

    # --- 3. توليد الصوت (AI Voice) ---
    print("🎙️ Generating AI Voiceover...")
    voice_path = "voice.mp3"
    communicate = edge_tts.Communicate(full_narrative, "en-US-GuyNeural")
    await communicate.save(voice_path)
    audio = AudioFileClip(voice_path)
    duration = audio.duration

    # --- 4. جلب فيديوهات متنوعة من Pexels ---
    print("🎬 Fetching cinematic clips from Pexels...")
    headers = {"Authorization": PEXELS_API}
    search_query = "luxury real estate mansion"
    pex_res = requests.get(f"https://api.pexels.com/videos/search?query={search_query}&per_page=8&orientation=portrait", headers=headers).json()
    
    clips = []
    total_clips_duration = 0
    for v in pex_res.get('videos', []):
        if total_clips_duration >= duration: break
        v_url = v['video_files'][0]['link']
        with open("temp_clip.mp4", "wb") as f:
            f.write(requests.get(v_url).content)
        
        c = VideoFileClip("temp_clip.mp4").resize(height=1920).without_audio()
        clips.append(c)
        total_clips_duration += c.duration

    # دمج المقاطع وقصها لتناسب طول الصوت
    print("✂️ Assembling the final video...")
    final_bg = concatenate_videoclips(clips).subclip(0, duration)
    final_video = final_bg.set_audio(audio)
    final_video.write_videofile("final.mp4", fps=24, codec="libx264", audio_codec="aac")

    # --- 5. تحسين العنوان والهاشتاجات ---
    # اختصار العنوان إذا تجاوز 100 حرف مع الحفاظ على المعنى
    clean_title = title if len(title) <= 100 else title[:97] + "..."
    extra_hashtags = "#LuxuryRealEstate #MansionTour #DreamHome #LuxuryLiving #Property"

    # --- 6. الرفع إلى Dailymotion ---
    print("🚀 Uploading to Dailymotion...")
    auth_data = {
        "grant_type": "password",
        "client_id": DM_KEY,
        "client_secret": DM_SECRET,
        "username": DM_USER,
        "password": DM_PASS,
        "scope": "manage_videos"
    }
    
    # الحصول على Access Token
    token_res = requests.post("https://api.dailymotion.com/oauth/token", data=auth_data).json()
    access_token = token_res.get("access_token")
    if not access_token:
        print("❌ Auth Failed! Check DM_USER/DM_PASS/API Keys.")
        return

    headers = {"Authorization": f"Bearer {access_token}"}
    
    # الحصول على رابط الرفع
    up_url = requests.get("https://api.dailymotion.com/file/upload", headers=headers).json()['upload_url']
    
    # رفع ملف الفيديو
    m = MultipartEncoder(fields={'file': ('final.mp4', open('final.mp4', 'rb'), 'video/mp4')})
    v_file_url = requests.post(up_url, data=m, headers={'Content-Type': m.content_type}).json()['url']
    
    # نشر الفيديو النهائي بالبيانات الذكية
    publish_data = {
        "url": v_file_url,
        "title": clean_title,
        "description": f"{title}\n\nRead the full article for more photos: {link}\n\n{extra_hashtags}",
        "published": "true",
        "channel": "lifestyle",
        "tags": "luxury,realestate,mansion,home",
        "is_created_for_kids": "false"
    }
    requests.post("https://api.dailymotion.com/me/videos", data=publish_data, headers=headers)

    # --- 7. تحديث الذاكرة ---
    with open("last_post.txt", "w") as f:
        f.write(title)
    
    print(f"✅ SUCCESS! '{title}' is now live on Dailymotion.")

if __name__ == "__main__":
    asyncio.run(main())
