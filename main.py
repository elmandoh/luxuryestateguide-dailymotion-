import feedparser, asyncio, edge_tts, requests, os, json
from groq import Groq # المكتبة الرسمية أضمن بكتير
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips
from requests_toolbelt import MultipartEncoder

# --- الإعدادات ---
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
PEXELS_API = os.getenv("PEXELS_API")
DM_KEY = os.getenv("DM_API_KEY")
DM_SECRET = os.getenv("DM_API_SECRET")
DM_USER = os.getenv("DM_USER")
DM_PASS = os.getenv("DM_PASS")

NEWS_RSS = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"

async def main():
    print("🔥 STEP 1: Fetching News...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(NEWS_RSS, headers=headers)
    feed = feedparser.parse(resp.content)
    
    if not feed.entries: return

    # منع التكرار
    processed = []
    if os.path.exists("last_post.txt"):
        with open("last_post.txt", "r") as f: processed = f.read().splitlines()

    target = next((e for e in feed.entries[:10] if e.title not in processed), None)
    if not target: print("⚠️ No new news."); return

    print(f"🌟 Story: {target.title}")

    # --- الخطوة 2: استخدام Groq (الطريقة الرسمية) ---
    print("🧠 STEP 2: Groq is thinking...")
    try:
        completion = client.chat.completions.create(
            model="llama3-8b-8192", # موديل سريع جداً ومستقر
            messages=[
                {"role": "system", "content": "Return ONLY JSON object."},
                {"role": "user", "content": f"Create viral video info for: {target.title}. JSON: script (30 words), search (1 word for pexels), title (with emojis), tags."}
            ],
            response_format={"type": "json_object"}
        )
        ai_data = json.loads(completion.choices[0].message.content)
    except Exception as e:
        print(f"❌ Groq Error: {e}"); return

    # --- الخطوة 3: الصوت ---
    print("🎙️ STEP 3: Voice Generation...")
    voice_path = "voice.mp3"
    await edge_tts.Communicate(ai_data['script'], "en-US-GuyNeural").save(voice_path)
    audio = AudioFileClip(voice_path)
    duration = audio.duration

    # --- الخطوة 4: فيديوهات Pexels ---
    print(f"📽️ STEP 4: Finding Videos for {ai_data['search']}...")
    h_pex = {"Authorization": PEXELS_API}
    v_res = requests.get(f"https://api.pexels.com/videos/search?query={ai_data['search']}&per_page=3&orientation=portrait", headers=h_pex).json()
    
    clips = []
    for i, v in enumerate(v_res.get('videos', [])):
        v_url = v['video_files'][0]['link']
        with open(f"v{i}.mp4", "wb") as f: f.write(requests.get(v_url).content)
        clip = VideoFileClip(f"v{i}.mp4").resized(height=1920).without_audio()
        clips.append(clip)

    # --- الخطوة 5: المونتاج ---
    print("🎬 STEP 5: Rendering...")
    final_bg = concatenate_videoclips(clips)
    if final_bg.duration < duration: final_bg = concatenate_videoclips([final_bg]*2)
    
    final_v = final_bg.subclipped(0, duration).with_audio(audio)
    final_v.write_videofile("final.mp4", fps=24, codec="libx264")

    # --- الخطوة 6: الرفع لـ Dailymotion ---
    print("🚀 STEP 6: Publishing...")
    auth = {"grant_type": "password", "client_id": DM_KEY, "client_secret": DM_SECRET, "username": DM_USER, "password": DM_PASS, "scope": "manage_videos"}
    token = requests.post("https://api.dailymotion.com/oauth/token", data=auth).json().get("access_token")
    
    if token:
        up_info = requests.get("https://api.dailymotion.com/file/upload", headers={"Authorization": f"Bearer {token}"}).json()
        m = MultipartEncoder(fields={'file': ('final.mp4', open('final.mp4', 'rb'), 'video/mp4')})
        f_url = requests.post(up_info['upload_url'], data=m, headers={'Content-Type': m.content_type}).json()['url']
        
        requests.post("https://api.dailymotion.com/me/videos", headers={"Authorization": f"Bearer {token}"}, data={
            "url": f_url,
            "title": ai_data['title'][:100],
            "description": f"{ai_data['script']}\n\n#news #trending",
            "tags": "news,trending,viral",
            "published": "true", "channel": "news"
        })
        with open("last_post.txt", "a") as f: f.write(target.title + "\n")
        print("✅ SUCCESS!")

if __name__ == "__main__":
    asyncio.run(main())
