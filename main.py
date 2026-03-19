import feedparser
import asyncio
import edge_tts
from moviepy.editor import ImageClip, AudioFileClip, TextClip, CompositeVideoClip
import os

# 1. جلب بيانات المدونة
BLOG_URL = "https://luxuryestateguide.blogspot.com/feeds/posts/default"

async def create_video():
    # قراءة المقال الأخير
    feed = feedparser.parse(BLOG_URL)
    if not feed.entries:
        print("No posts found!")
        return
    
    post = feed.entries[0]
    title = post.title
    
    # تحويل العنوان لصوت إنجليزي (مجاني)
    voice_file = "voice.mp3"
    communicate = edge_tts.Communicate(title, "en-US-GuyNeural")
    await communicate.save(voice_file)
    
    print(f"Done: Voice generated for {title}")
    # ملاحظة: سنضيف كود صنع الفيديو والرفع في الخطوة القادمة
    # لنتأكد أولاً أن البيئة تعمل

if __name__ == "__main__":
    asyncio.run(create_video())
