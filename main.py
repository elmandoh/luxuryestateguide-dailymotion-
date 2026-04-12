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

# مصدر الأخبار العالمية لضمان عائد مادي مرتفع
NEWS_RSS = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"

async def main():
    print("🚀 STEP 1: Fetching High-Value News...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(NEWS_RSS, headers=headers)
    feed = feedparser.parse(resp.content)
    
    if not feed.entries: return

    # فحص التكرار لمنع رفع نفس الفيديو مرتين
    processed = []
    if os.path.exists("last_post.txt"):
        with open("last_post.txt", "r") as f: processed = f.read().splitlines()

    target = next((e for e in feed.entries[:15] if e.title not in processed), None)
    if not target: 
        print("⚠️ No new news found."); return

    print(f"🌟 Target Story: {target.title}")

    # STEP 2: Groq AI - توليد بيانات الفيديو (سكريبت طويل + صورة مصغرة)
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
            {"role": "user", "content": f"""Create viral video data for: {target.title}. 
            1. script: Detailed report (at least 500 words). Focus on the financial impact, market reactions, and economic consequences of this news.
            2. search_queries: List of 10 keywords for Pexels.
            3. thumb_text: Extreme clickbait text (4 words max).
            4. title: Create a SHOCKING 'Hook' title. Use power words like 'Shocking', 'Finally Revealed', 'Market Crash', or 'The Money Secret'.
            5. tags: Investing, Passive Income, Crypto News, Market Analysis, Wealth."""}
            ],
            response_format={"type": "json_object"}
        )
        ai_data = json.loads(completion.choices[0].message.content)
    except Exception as e:
        print(f"❌ Groq Error: {e}"); return

    # --- تصحيح الخطأ (TypeError Fix) ---
    # التأكد أن السكريبت نص صريح وليس قائمة
    raw_script = ai_data.get('script', '')
    if isinstance(raw_script, list):
        clean_script = " ".join(map(str, raw_script))
    else:
        clean_script = str(raw_script)

    # STEP 3: Voice Generation
    print("🎙️ STEP 3: Generating Long Voiceover...")
    v_path = "voice.mp3"
    if clean_script.strip():
        await edge_tts.Communicate(clean_script, "en-US-GuyNeural").save(v_path)
    else:
        print("❌ Script is empty after cleaning."); return
    
    audio = AudioFileClip(v_path)

    # STEP 4: Finding Videos from Pexels
    print(f"📽️ STEP 4: Gathering Visuals for {len(ai_data['search_queries'])} queries...")
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
                if len(clips) >= 15: break 
        except: continue

    if not clips:
        print("❌ No videos found on Pexels."); return

    # STEP 5: Thumbnail Frame Hack (لحل مشكلة صورة دايلي موشن)
    print("🖼️ STEP 5: Creating Integrated Thumbnail Frame...")
    thumb_bg = ColorClip(size=(1920, 1080), color=(20, 20, 20)).with_duration(1.5)
    thumb_txt = TextClip(
        text=str(ai_data.get('thumb_text', 'BREAKING NEWS')).upper(),
        font_size=130,
        color='yellow',
        method='caption',
        size=(1700, None)
    ).with_duration(1.5).with_position('center')
    
    thumbnail_clip = CompositeVideoClip([thumb_bg, thumb_txt])

    # STEP 6: Rendering Final Video
    print("🎬 STEP 6: Rendering Final Long-Form Video...")
    video_content = concatenate_videoclips(clips, method="compose")
    
    while video_content.duration < audio.duration:
        video_content = concatenate_videoclips([video_content, video_content])
    
    main_video = video_content.subclipped(0, audio.duration).with_audio(audio)
    final_v = concatenate_videoclips([thumbnail_clip, main_video])
    final_v.write_videofile("final.mp4", fps=24, codec="libx264", audio_codec="aac")

    # STEP 7: Upload & Cleanup
    print("🚀 STEP 7: Publishing to Dailymotion...")
    auth = {
        "grant_type": "password",
        "client_id": DM_KEY,
        "client_secret": DM_SECRET,
        "username": DM_USER,
        "password": DM_PASS,
        "scope": "manage_videos"
    }
    
    token_resp = requests.post("https://api.dailymotion.com/oauth/token", data=auth).json()
    
    if "access_token" in token_resp:
        token = token_resp["access_token"]
        up_url = requests.get("https://api.dailymotion.com/file/upload", 
                               headers={"Authorization": f"Bearer {token}"}).json()['upload_url']
        
        m = MultipartEncoder(fields={'file': ('final.mp4', open('final.mp4', 'rb'), 'video/mp4')})
        f_url = requests.post(up_url, data=m, headers={'Content-Type': m.content_type}).json()['url']
        
# تجهيز الوصف وتنظيفه من أي JSON
        raw_description = ai_data.get('script', '')
        # إضافة الهاشتاجات الإماراتية والنيوز في نهاية الوصف
        uae_hashtags = "\n\n#UAE #Dubai #AbuDhabi #News #Trending #Emirates #WorldNews"
        full_description = f"{raw_description}{uae_hashtags}"

        # إنشاء الفيديو في القناة مع البيانات المصلحة
        create_v = requests.post("https://api.dailymotion.com/me/videos", 
                                 headers={"Authorization": f"Bearer {token}"}, 
                                 data={
                                     "url": f_url,
                                     "title": ai_data.get('title', target.title)[:100],
                                     "description": full_description[:1000],
                                     "published": "true",
                                     "channel": "news",
                                     "tags": ",".join(ai_data.get('tags', [])) + ",UAE,Dubai,Finance,News,Trending", # الفاصلة هنا هي الحل
                                     "is_created_for_kids": "false"
                                 }).json()
        
        if "id" in create_v:
            print(f"✅ SUCCESS! Video: https://www.dailymotion.com/video/{create_v['id']}")
            with open("last_post.txt", "a") as f: f.write(target.title + "\n")
            
            # تنظيف الملفات لتوفير المساحة في GitHub Actions
            os.remove("final.mp4")
            os.remove("voice.mp3")
            for f in os.listdir():
                if f.startswith("temp_"): os.remove(f)
    else:
        print(f"❌ Auth Failed: {token_resp}")

if __name__ == "__main__":
    asyncio.run(main())
