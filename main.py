import feedparser, asyncio, edge_tts, requests, os, json, random
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips
from requests_toolbelt import MultipartEncoder

# --- الإعدادات وجلب المفاتيح من البيئة ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PEXELS_API = os.getenv("PEXELS_API")
DM_KEY = os.getenv("DM_API_KEY")
DM_SECRET = os.getenv("DM_API_SECRET")
DM_USER = os.getenv("DM_USER")
DM_PASS = os.getenv("DM_PASS")

# رابط تريندات جوجل (Global - US) للحصول على أعلى بحث عالمي
TRENDS_RSS = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US"

def ask_groq(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "llama3-70b-8192",
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"}
    }
    response = requests.post(url, json=data, headers=headers)
    return response.json()['choices'][0]['message']['content']

async def main():
    print("🔥 STEP 1: Fetching Google Trends...")
    feed = feedparser.parse(TRENDS_RSS)
    if not feed.entries:
        print("❌ No trends found.")
        return
    
    # التأكد من عدم تكرار التريندات
    processed_trends = []
    if os.path.exists("last_post.txt"):
        with open("last_post.txt", "r") as f:
            processed_trends = f.read().splitlines()

    target_entry = None
    for entry in feed.entries[:10]: # فحص أول 10 تريندات
        if entry.title not in processed_trends:
            target_entry = entry
            break

    if not target_entry:
        print("⚠️ All current trends already processed.")
        return

    top_trend = target_entry.title
    print(f"🌟 Processing Trend: {top_trend}")

    # --- استخدام Groq لتوليد السكريبت وتفاصيل الفيديو ---
    print("🧠 STEP 2: Generating Script via Groq AI...")
    prompt = f"""
    Create a viral short video script about the trend '{top_trend}'. 
    The tone should be exciting. 
    Return ONLY a JSON object with these keys: 
    "script": "a 30-word engaging script in English",
    "search_term": "one specific keyword for Pexels videos",
    "title": "a viral title with emojis",
    "tags": "5 viral hashtags"
    """
    ai_json = json.loads(ask_groq(prompt))
    print(f"✅ AI Script Generated: {ai_json['script'][:50]}...")

    # --- توليد الصوت ---
    print("🎙️ STEP 3: Generating Voice...")
    voice_path = "voice.mp3"
    communicate = edge_tts.Communicate(ai_json['script'], "en-US-GuyNeural")
    await communicate.save(voice_path)
    audio = AudioFileClip(voice_path)
    duration = audio.duration

    # --- جلب فيديوهات Pexels ---
    print(f"📽️ STEP 4: Searching Pexels for: {ai_json['search_term']}")
    headers = {"Authorization": PEXELS_API}
    pex_url = f"https://api.pexels.com/videos/search?query={ai_json['search_term']}&per_page=5&orientation=portrait"
    pex_res = requests.get(pex_url, headers=headers).json()
    
    clips = []
    current_d = 0
    for i, v in enumerate(pex_res.get('videos', [])):
        v_url = v['video_files'][0]['link']
        temp_name = f"v_{i}.mp4"
        with open(temp_name, "wb") as f: f.write(requests.get(v_url).content)
        clip = VideoFileClip(temp_name).resized(height=1920).without_audio()
        clips.append(clip)
        current_d += clip.duration
        if current_d >= duration: break

    # --- المونتاج ---
    print("🎬 STEP 5: Editing Video...")
    final_bg = concatenate_videoclips(clips)
    if final_bg.duration < duration:
        final_bg = concatenate_videoclips([final_bg] * (int(duration/final_bg.duration) + 1))
    
    final_video = final_bg.subclipped(0, duration).with_audio(audio)
    final_video.write_videofile("final.mp4", fps=24, codec="libx264", audio_codec="aac")

    # --- الرفع لـ Dailymotion ---
    print(f"🚀 STEP 6: Uploading to Dailymotion: {ai_json['title']}")
    auth_data = {
        "grant_type": "password", "client_id": DM_KEY, 
        "client_secret": DM_SECRET, "username": DM_USER, "password": DM_PASS, "scope": "manage_videos"
    }
    r = requests.post("https://api.dailymotion.com/oauth/token", data=auth_data)
    if r.status_code == 200:
        token = r.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # طلب رابط الرفع
        up_url_res = requests.get("https://api.dailymotion.com/file/upload", headers=headers).json()
        up_url = up_url_res['upload_url']
        
        # رفع الملف الحقيقي
        m = MultipartEncoder(fields={'file': ('final.mp4', open('final.mp4', 'rb'), 'video/mp4')})
        file_url = requests.post(up_url, data=m, headers={'Content-Type': m.content_type}).json()['url']
        
        # نشر الفيديو بالبيانات الجذابة من AI
        requests.post("https://api.dailymotion.com/me/videos", headers=headers, data={
            "url": file_url,
            "title": ai_json['title'][:100],
            "description": f"{ai_json['script']}\n\n#trending #news {ai_json['tags']}",
            "tags": ai_json['tags'].replace("#", ""),
            "published": "true",
            "channel": "news"
        })
        
        # تسجيل التريند كـ "تمت معالجته"
        with open("last_post.txt", "a") as f:
            f.write(top_trend + "\n")
        print("✅ SUCCESS: Video is live!")
    else:
        print(f"❌ Upload failed. Auth response: {r.text}")

if __name__ == "__main__":
    asyncio.run(main())
