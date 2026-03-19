import feedparser
import asyncio
import edge_tts
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, TextClip, CompositeVideoClip
import requests
import os
from requests_toolbelt import MultipartEncoder

# جلب المفاتيح من GitHub Secrets
PEXELS_API_KEY = os.getenv("PEXELS_API")
DM_API_KEY = os.getenv("DM_API_KEY")
DM_API_SECRET = os.getenv("DM_API_SECRET")
DM_USER = os.getenv("DM_USER")
DM_PASS = os.getenv("DM_PASS")

BLOG_URL = "https://luxuryestateguide.blogspot.com/feeds/posts/default"

async def main():
    # 1. جلب المقال
    feed = feedparser.parse(BLOG_URL)
    title = feed.entries[0].title
    print(f"Processing: {title}")

    # 2. توليد الصوت
    await edge_tts.Communicate(title, "en-US-GuyNeural").save("voice.mp3")
    audio = AudioFileClip("voice.mp3")

    # 3. جلب فيديوهات من Pexels
    headers = {"Authorization": PEXELS_API_KEY}
    res = requests.get(f"https://api.pexels.com/videos/search?query=luxury+estate&per_page=2&orientation=portrait", headers=headers).json()
    
    video_url = res['videos'][0]['video_files'][0]['link']
    with open("temp.mp4", "wb") as f: f.write(requests.get(video_url).content)
    
    # 4. صناعة الفيديو
    clip = VideoFileClip("temp.mp4").resize(height=1920).subclip(0, audio.duration).without_audio()
    final = CompositeVideoClip([clip]).set_audio(audio)
    final.write_videofile("final.mp4", fps=24)

    # 5. الرفع لديلى موشن (Dailymotion Upload)
    # ملاحظة: سنستخدم مكتبة Requests للرفع المباشر عبر الـ API
    print("Uploading to Dailymotion...")
    # (هنا يتم استدعاء الـ API لرفع الملف final.mp4)

if __name__ == "__main__":
    asyncio.run(main())
