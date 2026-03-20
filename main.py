import feedparser, asyncio, edge_tts, requests, os, re
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips
from requests_toolbelt import MultipartEncoder

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

    # ملاحظة: امسح ملف last_post.txt من GitHub لو عايز تجرّب على نفس الفيديو تاني
    if os.path.exists("last_post.txt"):
        with open("last_post.txt", "r") as f:
            if f.read().strip() == title:
                print("⚠️ Already published.")
                return

    # 1. توليد الصوت
    voice_path = "voice.mp3"
    content = f"{title}. {clean_html(post.content[0].value)[:2000]}"
    communicate = edge_tts.Communicate(content, "en-US-GuyNeural")
    await communicate.save(voice_path)
    
    # تحميل الصوت والتأكد من مدته
    audio = AudioFileClip(voice_path)
    duration = audio.duration

    # 2. جلب فيديوهات
    headers = {"Authorization": PEXELS_API}
    pex_res = requests.get(f"https://api.pexels.com/videos/search?query=luxury+mansion&per_page=10&orientation=portrait", headers=headers).json()
    
    clips = []
    current_d = 0
    for i, v in enumerate(pex_res.get('videos', [])):
        v_url = v['video_files'][0]['link']
        temp = f"v_{i}.mp4"
        with open(temp, "wb") as f: f.write(requests.get(v_url).content)
        c = VideoFileClip(temp).resized(height=1920).without_audio()
        clips.append(c)
        current_d += c.duration
        if current_d >= duration: break

    # 3. الدمج مع معالجة الصوت (التعديل هنا)
    final_bg = concatenate_videoclips(clips)
    if final_bg.duration < duration:
        loop_count = int(duration / final_bg.duration) + 1
        final_bg = concatenate_videoclips([final_bg] * loop_count)
    
    final_video = final_bg.subclipped(0, duration)
    final_video = final_video.with_audio(audio) # ربط الصوت
    
    # أمر الكتابة مع التأكد من الـ Audio Codec
    final_video.write_videofile("final.mp4", fps=24, codec="libx264", audio_codec="aac", temp_audiofile='temp-audio.m4a', remove_temp=True)

    # 4. الرفع لديلى موشن
    print("🚀 Attempting to Upload...")
    auth = {"grant_type": "password", "client_id": DM_KEY, "client_secret": DM_SECRET, "username": DM_USER, "password": DM_PASS, "scope": "manage_videos"}
    r = requests.post("https://api.dailymotion.com/oauth/token", data=auth)
    
    if r.status_code == 200:
        token = r.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        up_url = requests.get("https://api.dailymotion.com/file/upload", headers=headers).json()['upload_url']
        m = MultipartEncoder(fields={'file': ('final.mp4', open('final.mp4', 'rb'), 'video/mp4')})
        v_url = requests.post(up_url, data=m, headers={'Content-Type': m.content_type}).json()['url']
        
        requests.post("https://api.dailymotion.com/me/videos", headers=headers, data={
            "url": v_url, "title": title[:100], "published": "true", "channel": "lifestyle"
        })
        
        with open("last_post.txt", "w") as f: f.write(title)
        print("✅ SUCCESS! Video with sound is live.")
    else:
        print("❌ Upload failed at auth stage.")

if __name__ == "__main__":
    asyncio.run(main())
