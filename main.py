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

# مصدر أخبار الألعاب
NEWS_RSS = "https://www.ign.com/rss/articles/feed.xml"

async def main():
    print("🚀 STEP 1: Fetching Gaming Stories...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(NEWS_RSS, headers=headers)
    feed = feedparser.parse(resp.content)
    
    if not feed.entries: return

    processed = []
    if os.path.exists("last_post.txt"):
        with open("last_post.txt", "r") as f: processed = f.read().splitlines()

    target = next((e for e in feed.entries[:15] if e.title not in processed), None)
    if not target: 
        print("⚠️ No new stories found."); return

    print(f"🌟 Target Story: {target.title}")

    # STEP 2: Groq AI - توليد قصة Lore وتاجات جيمنج
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Return ONLY a valid JSON object. You are a professional Gaming Lore expert."},
                {"role": "user", "content": f"""Create viral GAMING LORE video data for: {target.title}. 
                1. script: Write an immersive, mysterious story (at least 600 words) about the history or secrets of this topic.
                2. search_queries: List of 12 keywords for Pexels visuals.
                3. thumb_text: LORE: UNTOLD SECRETS.
                4. title: Create a SHOCKING title like '[Game] 2026: The Ultimate Lore'.
                5. tags: Gaming, Lore, Secrets, Mystery, 2026."""}
            ],
            response_format={"type": "json_object"}
        )
        ai_data = json.loads(completion.choices[0].message.content)
    except Exception as e:
        print(f"❌ Groq Error: {e}"); return

    raw_script = ai_data.get('script', '')
    clean_script = " ".join(raw_script) if isinstance(raw_script, list) else str(raw_script)

    # STEP 3: Voice Generation
    print("🎙️ STEP 3: Generating Voiceover...")
    v_path = "voice.mp3"
    await edge_tts.Communicate(clean_script, "en-US-GuyNeural").save(v_path)
    audio = AudioFileClip(v_path)

    # STEP 4: Gathering Visuals
    print("📽️ STEP 4: Gathering Visuals...")
    h_pex = {"Authorization": PEXELS_API}
    clips = []
    for query in ai_data['search_queries']:
        v_url_api = f"https://api.pexels.com/videos/search?query={query}&per_page=2&orientation=landscape"
        try:
            v_res = requests.get(v_url_api, headers=h_pex).json()
            for v in v_res.get('videos', []):
                v_url = v['video_files'][0]['link']
                v_name = f"temp_{len(clips)}.mp4"
                with open(v_name, "wb") as f: f.write(requests.get(v_url).content)
                clip = VideoFileClip(v_name).resized(width=1920).without_audio()
                clips.append(clip)
                if len(clips) >= 20: break 
        except: continue

    if not clips: return

    # STEP 5: Thumbnail Frame
    thumb_bg = ColorClip(size=(1920, 1080), color=(15, 15, 15)).with_duration(1.5)
    thumb_txt = TextClip(text="GAMING LORE", font_size=150, color='yellow', size=(1800, None), method='caption').with_duration(1.5).with_position('center')
    thumbnail_clip = CompositeVideoClip([thumb_bg, thumb_txt])

    # STEP 6: Rendering
    print("🎬 STEP 6: Rendering Video...")
    video_content = concatenate_videoclips(clips, method="compose")
    while video_content.duration < audio.duration:
        video_content = concatenate_videoclips([video_content, video_content])
    main_video = video_content.subclipped(0, audio.duration).with_audio(audio)
    final_v = concatenate_videoclips([thumbnail_clip, main_video])
    final_v.write_videofile("final.mp4", fps=24, codec="libx264")

    # STEP 7: Upload & Cleanup
    print("🚀 STEP 7: Publishing to Dailymotion...")
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
                                     "description": f"{clean_script[:2900]}\n\n#Gaming #Lore #Mystery",
                                     "published": "true",
                                     "channel": "videogames", # القسم المخصص للألعاب
                                     "tags": "Gaming,Lore,Mystery,2026",
                                     "is_created_for_kids": "false"
                                 }).json()
        
        if "id" in create_v:
            print(f"\n✅ SUCCESS! Video URL: https://www.dailymotion.com/video/{create_v['id']}\n")
            with open("last_post.txt", "a") as f: f.write(target.title + "\n")
            
            os.remove("final.mp4")
            os.remove("voice.mp3")
            for f in os.listdir():
                if f.startswith("temp_"): os.remove(f)
    else:
        print("❌ Auth Failed")

if __name__ == "__main__":
    asyncio.run(main())
