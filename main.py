import feedparser, asyncio, edge_tts, requests, os, json
from groq import Groq
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips, TextClip, CompositeVideoClip, ColorClip
from requests_toolbelt import MultipartEncoder

# الإعدادات من GitHub Secrets
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
PEXELS_API = os.getenv("PEXELS_API")
DM_KEY = os.getenv("DM_API_KEY")
DM_SECRET = os.getenv("DM_API_SECRET")
DM_USER = os.getenv("DM_USER")
DM_PASS = os.getenv("DM_PASS")

# مصادر أخبار الألعاب - هنستخدم أكتر من مصدر لضمان الشغل
NEWS_SOURCES = [
    "https://www.gamespot.com/feeds/news/",
    "https://www.ign.com/rss/articles/feed.xml"
]

async def main():
    print("🚀 STEP 1: Fetching Gaming Stories...")
    feed = None
    for url in NEWS_SOURCES:
        try:
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            temp_feed = feedparser.parse(resp.content)
            if temp_feed.entries:
                feed = temp_feed
                print(f"✅ Success fetching from: {url}")
                break
        except: continue

    if not feed or not feed.entries:
        print("❌ ALL RSS Sources failed. Checking connection..."); return

    target = feed.entries[0]
    print(f"🌟 Target Story: {target.title}")

    # STEP 2: Groq AI
    print("🤖 STEP 2: Generating Lore Script...")
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Return ONLY a valid JSON object. You are a Gaming Lore expert."},
                {"role": "user", "content": f"""Create viral GAMING LORE for: {target.title}. 
                1. script: Mysterious story (600 words).
                2. search_queries: 12 keywords for Pexels.
                3. thumb_text: LORE SECRETS.
                4. title: Shocking Lore Title.
                5. tags: Gaming, Lore, Secrets, 2026."""}
            ],
            response_format={"type": "json_object"}
        )
        ai_data = json.loads(completion.choices[0].message.content)
    except Exception as e:
        print(f"❌ Groq Error: {e}"); return

    clean_script = str(ai_data.get('script', ''))

    # STEP 3: Voice
    print("🎙️ STEP 3: Generating Voiceover...")
    await edge_tts.Communicate(clean_script, "en-US-GuyNeural").save("voice.mp3")
    audio = AudioFileClip("voice.mp3")

    # STEP 4: Visuals
    print("📽️ STEP 4: Gathering Visuals...")
    clips = []
    h_pex = {"Authorization": PEXELS_API}
    for query in ai_data['search_queries'][:8]: # تقليل الكويريز لسرعة البحث
        try:
            v_res = requests.get(f"https://api.pexels.com/videos/search?query={query}&per_page=1", headers=h_pex).json()
            for v in v_res.get('videos', []):
                v_url = v['video_files'][0]['link']
                v_name = f"temp_{len(clips)}.mp4"
                with open(v_name, "wb") as f: f.write(requests.get(v_url).content)
                clips.append(VideoFileClip(v_name).resized(width=1920).without_audio())
        except: continue

    if not clips: return

    # STEP 5 & 6: Rendering
    print("🎬 STEP 6: Rendering (Be patient)...")
    video_content = concatenate_videoclips(clips, method="compose")
    while video_content.duration < audio.duration:
        video_content = concatenate_videoclips([video_content, video_content])
    
    final_v = video_content.subclipped(0, audio.duration).with_audio(audio)
    final_v.write_videofile("final.mp4", fps=24, codec="libx264")

    # STEP 7: Upload
    print("🚀 STEP 7: Publishing...")
    auth = {"grant_type": "password", "client_id": DM_KEY, "client_secret": DM_SECRET, "username": DM_USER, "password": DM_PASS, "scope": "manage_videos"}
    token_resp = requests.post("https://api.dailymotion.com/oauth/token", data=auth).json()
    
    if "access_token" in token_resp:
        token = token_resp["access_token"]
        up_url = requests.get("https://api.dailymotion.com/file/upload", headers={"Authorization": f"Bearer {token}"}).json()['upload_url']
        m = MultipartEncoder(fields={'file': ('final.mp4', open('final.mp4', 'rb'), 'video/mp4')})
        f_url = requests.post(up_url, data=m, headers={'Content-Type': m.content_type}).json()['url']
        
        create_v = requests.post("https://api.dailymotion.com/me/videos", 
                                 headers={"Authorization": f"Bearer {token}"}, 
                                 data={
                                     "url": f_url,
                                     "title": ai_data.get('title', target.title)[:100],
                                     "description": f"{clean_script[:2800]}\n\n#Gaming #Lore #2026",
                                     "published": "true",
                                     "channel": "videogames", 
                                     "tags": "Gaming,Lore,Mystery",
                                     "is_created_for_kids": "false"
                                 }).json()
        
        if "id" in create_v:
            print("\n" + "="*50)
            print(f"🔥 VIDEO READY: https://www.dailymotion.com/video/{create_v['id']}")
            print("="*50 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
