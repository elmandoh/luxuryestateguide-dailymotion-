import feedparser, asyncio, edge_tts, requests, os, json
from groq import Groq
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips, TextClip, CompositeVideoClip, ColorClip
from requests_toolbelt import MultipartEncoder

# الإعدادات
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
PEXELS_API = os.getenv("PEXELS_API")
DM_KEY = os.getenv("DM_API_KEY")
DM_SECRET = os.getenv("DM_API_SECRET")
DM_USER = os.getenv("DM_USER")
DM_PASS = os.getenv("DM_PASS")

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
                break
        except: continue

    if not feed or not feed.entries: return

    target = feed.entries[0]
    print(f"🌟 Target Story: {target.title}")

    # STEP 2: Groq AI
    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "Return ONLY a valid JSON object. You are a Gaming Lore expert."},
            {"role": "user", "content": f"Create viral GAMING LORE for: {target.title}. JSON with: script (600 words), search_queries (12 keywords), title."}
        ],
        response_format={"type": "json_object"}
    )
    ai_data = json.loads(completion.choices[0].message.content)
    clean_script = str(ai_data.get('script', ''))

    # STEP 3: Voice - حل مشكلة الـ mp3
    v_path = "voice.mp3"
    await edge_tts.Communicate(clean_script, "en-US-GuyNeural").save(v_path)
    
    # تحميل الصوت مع معالجة الخطأ
    try:
        audio = AudioFileClip(v_path)
    except:
        print("❌ Audio loading failed"); return

    # STEP 4: Visuals
    clips = []
    h_pex = {"Authorization": PEXELS_API}
    for query in ai_data.get('search_queries', [])[:8]:
        try:
            v_res = requests.get(f"https://api.pexels.com/videos/search?query={query}&per_page=1", headers=h_pex).json()
            for v in v_res.get('videos', []):
                v_url = v['video_files'][0]['link']
                v_name = f"temp_{len(clips)}.mp4"
                with open(v_name, "wb") as f: f.write(requests.get(v_url).content)
                # استخدام ريزولوشن ثابت لضمان النجاح
                clips.append(VideoFileClip(v_name).resized(width=1280).without_audio())
        except: continue

    # STEP 5 & 6: Rendering
    print("🎬 STEP 6: Rendering Final Video...")
    video_content = concatenate_videoclips(clips, method="compose")
    while video_content.duration < audio.duration:
        video_content = concatenate_videoclips([video_content, video_content])
    
    final_v = video_content.subclipped(0, audio.duration).with_audio(audio)
    # تعديل بارامترات الرندر لحل مشكلة الـ Invalid Data
    final_v.write_videofile("final.mp4", fps=24, codec="libx264", audio_codec="aac", temp_audiofile='temp-audio.m4a', remove_temp=True)

    # STEP 7: Upload
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
                          "description": clean_script[:2800],
                          "published": "true",
                          "channel": "videogames",
                          "is_created_for_kids": "false"
                      }).json()
        
        if "id" in create_v:
            print(f"✅ SUCCESS! https://www.dailymotion.com/video/{create_v['id']}")

    audio.close()
    for clip in clips: clip.close()

if __name__ == "__main__":
    asyncio.run(main())
