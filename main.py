import feedparser, asyncio, edge_tts, requests, os
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip
from requests_toolbelt import MultipartEncoder

# جلب الإعدادات من Secrets
PEXELS_API = os.getenv("PEXELS_API")
DM_KEY = os.getenv("DM_API_KEY")
DM_SECRET = os.getenv("DM_API_SECRET")
DM_USER = os.getenv("DM_USER")
DM_PASS = os.getenv("DM_PASS")

BLOG_FEED = "https://luxuryestateguide.blogspot.com/feeds/posts/default"

async def main():
    # 1. جلب المقال
    feed = feedparser.parse(BLOG_FEED)
    if not feed.entries: return
    post = feed.entries[0]
    title = post.title
    link = post.link
    print(f"🌟 Processing: {title}")

    # 2. توليد الصوت (إنجليزي)
    voice_path = "voice.mp3"
    await edge_tts.Communicate(title, "en-US-GuyNeural").save(voice_path)
    audio = AudioFileClip(voice_path)

    # 3. جلب فيديو من Pexels
    headers = {"Authorization": PEXELS_API}
    pex_res = requests.get(f"https://api.pexels.com/videos/search?query=luxury+home&per_page=1&orientation=portrait", headers=headers).json()
    v_url = pex_res['videos'][0]['video_files'][0]['link']
    with open("temp.mp4", "wb") as f: f.write(requests.get(v_url).content)
    
    # 4. مونتاج الفيديو
    clip = VideoFileClip("temp.mp4").resize(height=1920).subclip(0, audio.duration).without_audio()
    final_video = clip.set_audio(audio)
    final_video.write_videofile("final.mp4", fps=24)

    # 5. الرفع لديلى موشن
    print("🚀 Uploading to Dailymotion...")
    auth_data = {"grant_type": "password", "client_id": DM_KEY, "client_secret": DM_SECRET, "username": DM_USER, "password": DM_PASS, "scope": "manage_videos"}
    token = requests.post("https://api.dailymotion.com/oauth/token", data=auth_data).json().get("access_token")
    
    headers = {"Authorization": f"Bearer {token}"}
    up_url = requests.get("https://api.dailymotion.com/file/upload", headers=headers).json()['upload_url']
    
    m = MultipartEncoder(fields={'file': ('final.mp4', open('final.mp4', 'rb'), 'video/mp4')})
    v_file_url = requests.post(up_url, data=m, headers={'Content-Type': m.content_type}).json()['url']
    
    publish_data = {"url": v_file_url, "title": title, "description": f"Full details here: {link}", "published": "true", "channel": "tech", "is_created_for_kids": "false"}
    requests.post("https://api.dailymotion.com/me/videos", data=publish_data, headers=headers)
    print("✅ Success! Video is live.")

if __name__ == "__main__":
    asyncio.run(main())
