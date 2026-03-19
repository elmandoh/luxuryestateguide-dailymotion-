import feedparser, asyncio, edge_tts, requests, os, re
# استدعاء مباشر للأدوات لتجنب مشكلة الـ editor
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.compositing.concatenate import concatenate_videoclips
from requests_toolbelt import MultipartEncoder

# إعدادات البيئة
os.environ["IMAGEIO_FFMPEG_EXE"] = "/usr/bin/ffmpeg"

PEXELS_API = os.getenv("PEXELS_API")
DM_KEY = os.getenv("DM_API_KEY")
DM_SECRET = os.getenv("DM_API_SECRET")
DM_USER = os.getenv("DM_USER")
DM_PASS = os.getenv("DM_PASS")
BLOG_FEED = "https://luxuryestateguide.blogspot.com/feeds/posts/default"

def clean_html(raw_html):
    cleanr = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')
    return re.sub(cleanr, '', raw_html)

async def main():
    print("🔍 Checking for new posts...")
    feed = feedparser.parse(BLOG_FEED)
    if not feed.entries: return
    
    post = feed.entries[0]
    title = post.title
    
    if os.path.exists("last_post.txt"):
        with open("last_post.txt", "r") as f:
            if f.read().strip() == title:
                print("⚠️ Already published.")
                return

    print(f"🌟 New Post: {title}")

    # توليد الصوت
    voice_path = "voice.mp3"
    communicate = edge_tts.Communicate(f"{title}. {clean_html(post.content[0].value)[:2000]}", "en-US-GuyNeural")
    await communicate.save(voice_path)
    audio = AudioFileClip(voice_path)
    duration = audio.duration

    # جلب الفيديوهات
    headers = {"Authorization": PEXELS_API}
    pex_res = requests.get(f"https://api.pexels.com/videos/search?query=luxury+mansion&per_page=5&orientation=portrait", headers=headers).json()
    
    clips = []
    total_d = 0
    for i, v in enumerate(pex_res.get('videos', [])):
        if total_d >= duration: break
        v_url = v['video_files'][0]['link']
        with open(f"v_{i}.mp4", "wb") as f: f.write(requests.get(v_url).content)
        
        # استدعاء مباشر للفيديو
        c = VideoFileClip(f"v_{i}.mp4").resize(height=1920).without_audio()
        clips.append(c)
        total_d += c.duration

    print("✂️ Finalizing video...")
    final_video = concatenate_videoclips(clips).subclip(0, duration).set_audio(audio)
    final_video.write_videofile("final.mp4", fps=24, codec="libx264", audio_codec="aac")

    # الرفع لديلى موشن
    auth = {"grant_type": "password", "client_id": DM_KEY, "client_secret": DM_SECRET, "username": DM_USER, "password": DM_PASS, "scope": "manage_videos"}
    token = requests.post("https://api.dailymotion.com/oauth/token", data=auth).json().get("access_token")
    
    headers = {"Authorization": f"Bearer {token}"}
    up_url = requests.get("https://api.dailymotion.com/file/upload", headers=headers).json()['upload_url']
    
    m = MultipartEncoder(fields={'file': ('final.mp4', open('final.mp4', 'rb'), 'video/mp4')})
    v_url = requests.post(up_url, data=m, headers={'Content-Type': m.content_type}).json()['url']
    
    requests.post("https://api.dailymotion.com/me/videos", headers=headers, data={
        "url": v_url, "title": title[:100], "published": "true", "channel": "lifestyle"
    })

    with open("last_post.txt", "w") as f: f.write(title)
    print("✅ Done!")

if __name__ == "__main__":
    asyncio.run(main())
