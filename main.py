import feedparser, asyncio, edge_tts, requests, os, json
from groq import Groq
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips
from requests_toolbelt import MultipartEncoder

# --- الإعدادات من GitHub Secrets ---
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
PEXELS_API = os.getenv("PEXELS_API")
DM_KEY = os.getenv("DM_API_KEY")
DM_SECRET = os.getenv("DM_API_SECRET")
DM_USER = os.getenv("DM_USER")
DM_PASS = os.getenv("DM_PASS")

NEWS_RSS = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"

async def main():
    print("🚀 STEP 1: Fetching News...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(NEWS_RSS, headers=headers)
    feed = feedparser.parse(resp.content)
    
    if not feed.entries: return

    processed = []
    if os.path.exists("last_post.txt"):
        with open("last_post.txt", "r") as f: processed = f.read().splitlines()

    target = next((e for e in feed.entries[:10] if e.title not in processed), None)
    if not target: 
        print("⚠️ No new news found."); return

    print(f"🌟 Target Story: {target.title}")

    # STEP 2: Groq AI - طلب 400 كلمة لضمان فيديو طويل +60 ثانية
    print("🤖 STEP 2: Generating 400-word Script...")
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Return ONLY JSON. Ensure the 'script' key contains approximately 400 words."},
                {"role": "user", "content": f"Create viral video data for: {target.title}. JSON keys: script (400 words), search (1 keyword), title, tags."}
            ],
            response_format={"type": "json_object"}
        )
        ai_data = json.loads(completion.choices[0].message.content)
        
        # حماية ضد القيم الفارغة التي تسببت في الخطأ السابق
        if 'script' not in ai_data or not ai_data['script']:
            raise ValueError("AI returned an empty script")
            
    except Exception as e:
        print(f"❌ Groq Error: {e}"); return

    # STEP 3: Voice Generation
    print("🎙️ STEP 3: Generating Voice...")
    v_path = "voice.mp3"
    # تحويل النص صراحة إلى سلسلة نصية لمنع خطأ TypeError
    script_text = str(ai_data['script'])
    await edge_tts.Communicate(script_text, "en-US-GuyNeural").save(v_path)
    audio = AudioFileClip(v_path)
    print(f"⏳ Audio Duration: {audio.duration} seconds")

    # STEP 4: Finding Videos (زيادة عدد اللقطات لـ 15 لتغطية المدة الطويلة)
    print(f"📽️ STEP 4: Finding Videos for {ai_data['search']}...")
    h_pex = {"Authorization": PEXELS_API}
    v_res = requests.get(f"https://api.pexels.com/videos/search?query={ai_data['search']}&per_page=15&orientation=portrait", headers=h_pex).json()
    
    clips = []
    for i, v in enumerate(v_res.get('videos', [])):
        try:
            v_url = v['video_files'][0]['link']
            v_name = f"v{i}.mp4"
            with open(v_name, "wb") as f: f.write(requests.get(v_url).content)
            clip = VideoFileClip(v_name).resized(height=1920).without_audio()
            clips.append(clip)
        except: continue

    if not clips:
        print("❌ No videos found on Pexels."); return

    # STEP 5: Editing & Rendering
    print("🎬 STEP 5: Rendering Final Video...")
    final_bg = concatenate_videoclips(clips, method="compose")
    
    # تكرار الخلفية حتى تغطي مدة الصوت الطويلة (400 كلمة)
    while final_bg.duration < audio.duration: 
        final_bg = concatenate_videoclips([final_bg, final_bg])
    
    final_v = final_bg.subclipped(0, audio.duration).with_audio(audio)
    # استخدام threads لتسريع الرندرة في GitHub Actions
    final_v.write_videofile("final.mp4", fps=24, codec="libx264", threads=4)

    # STEP 6: Upload to Dailymotion
    print("🚀 STEP 6: Publishing to Dailymotion...")
    auth = {
        "grant_type": "password",
        "client_id": DM_KEY,
        "client_secret": DM_SECRET,
        "username": DM_USER,
        "password": DM_PASS,
        "scope": "manage_videos"
    }
    
    token_resp = requests.post("https://api.dailymotion.com/oauth/token", data=auth)
    token_data = token_resp.json()
    
    if "access_token" in token_data:
        token = token_data["access_token"]
        up_url_resp = requests.get("https://api.dailymotion.com/file/upload", 
                                   headers={"Authorization": f"Bearer {token}"}).json()
        up_url = up_url_resp.get('upload_url')
        
        m = MultipartEncoder(fields={'file': ('final.mp4', open('final.mp4', 'rb'), 'video/mp4')})
        f_url = requests.post(up_url, data=m, headers={'Content-Type': m.content_type}).json()['url']
        
        create_v = requests.post("https://api.dailymotion.com/me/videos", 
                                 headers={"Authorization": f"Bearer {token}"}, 
                                 data={
                                     "url": f_url,
                                     "title": ai_data['title'][:100],
                                     "description": ai_data['script'],
                                     "published": "true",
                                     "channel": "news",
                                     "is_created_for_kids": "false"
                                 }).json()
        
        if "id" in create_v:
            print(f"✅ DONE! Video Live at: https://www.dailymotion.com/video/{create_v['id']}")
            with open("last_post.txt", "a") as f: f.write(target.title + "\n")
        else:
            print(f"❌ Creation Failed: {create_v}")
    else:
        print(f"❌ Auth Failed: {token_data}")

    # تنظيف الملفات المؤقتة لتوفير مساحة
    print("🧹 Cleaning up...")
    for file in [f"v{i}.mp4" for i in range(len(clips))] + ["voice.mp3", "final.mp4"]:
        if os.path.exists(file): os.remove(file)

if __name__ == "__main__":
    asyncio.run(main())
