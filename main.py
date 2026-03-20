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

    # 3. الدمج
    final_bg = concatenate_videoclips(clips)
    if final_bg.duration < duration:
        loop_count = int(duration / final_bg.duration) + 1
        final_bg = concatenate_videoclips([final_bg] * loop_count)
    
    final_video = final_bg.subclipped(0, duration).with_audio(audio)
    final_video.write_videofile("final.mp4", fps=24, codec="libx264", audio_codec="aac")

 # جزء الرفع المطور لمعرفة سبب الخطأ
    print("🚀 Attempting to Upload...")
    auth = {
        "grant_type": "password",
        "client_id": DM_KEY,
        "client_secret": DM_SECRET,
        "username": DM_USER,
        "password": DM_PASS,
        "scope": "manage_videos"
    }
    
    r = requests.post("https://api.dailymotion.com/oauth/token", data=auth)
    print(f"Auth Response: {r.status_code}") # هيطبع كود الاستجابة
    
    if r.status_code != 200:
        print(f"❌ Login Failed! Reason: {r.text}") # هيقولنا السبب الحقيقي هنا
        return
        
    token_data = r.json()
    token = token_data.get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    # طلب رابط الرفع
    up_req = requests.get("https://api.dailymotion.com/file/upload", headers=headers)
    if up_req.status_code != 200:
        print(f"❌ Could not get upload URL: {up_req.text}")
        return
    
    upload_data = up_req.json()
    if 'upload_url' not in upload_data:
        print(f"❌ upload_url missing! Full response: {upload_data}")
        return

    up_url = upload_data['upload_url']
    print(f"✅ Got Upload URL: {up_url}")
    
    # النشر النهائي
    requests.post("https://api.dailymotion.com/me/videos", headers=headers, data={
        "url": v_url, 
        "title": title[:100], 
        "description": f"{title}\n\n#luxury #realestate",
        "published": "true", 
        "channel": "lifestyle"
    })

    with open("last_post.txt", "w") as f: f.write(title)
    print("✅ SUCCESS! Video is live.")

if __name__ == "__main__":
    asyncio.run(main())
