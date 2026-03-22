import feedparser, asyncio, edge_tts, requests, os, json, re
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips
from requests_toolbelt import MultipartEncoder

# --- جلب المفاتيح من GitHub Secrets ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PEXELS_API = os.getenv("PEXELS_API")
DM_KEY = os.getenv("DM_API_KEY")
DM_SECRET = os.getenv("DM_API_SECRET")
DM_USER = os.getenv("DM_USER")
DM_PASS = os.getenv("DM_PASS")

# رابط أخبار جوجل (World News) لضمان الاستقرار والتريندات العالمية
NEWS_RSS = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"

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
    print("🔥 STEP 1: Fetching Trending Stories...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124'}
    
    try:
        resp = requests.get(NEWS_RSS, headers=headers, timeout=20)
        feed = feedparser.parse(resp.content)
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return

    if not feed.entries:
        print("❌ No news found.")
        return

    # فحص التكرار من ملف last_post.txt
    processed = []
    if os.path.exists("last_post.txt"):
        with open("last_post.txt", "r") as f: processed = f.read().splitlines()

    target = None
    for entry in feed.entries[:10]:
        if entry.title not in processed:
            target = entry
            break

    if not target:
        print("⚠️ No new stories to process.")
        return

    title_trend = target.title
    print(f"🌟 Target Story: {title_trend}")

    # --- الخطوة 2: ذكاء Groq لتوليد السكريبت ---
    print("🧠 STEP 2: Generating Content via Groq...")
    prompt = f"""
    Create a viral short video script for this news: '{title_trend}'.
    Format the response as JSON with these keys:
    "script": "Exciting 30-word summary in English",
    "search_term": "Best 1-word keyword for Pexels videos",
    "video_title": "Viral title with emojis",
    "tags": "5 viral hashtags"
    """
    
    ai_data = json.loads(ask_groq(prompt))
    print(f"✅ AI Script: {ai_data['script'][:50]}...")

    # --- الخطوة 3: تحويل النص لصوت ---
    print("🎙️ STEP 3: Voice Generation...")
    voice_path = "voice.mp3"
    await edge_tts.Communicate(ai_data['script'], "en-US-GuyNeural").save(voice_path)
    audio = AudioFileClip(voice_path)
    duration = audio.duration

    # --- الخطوة 4: جلب فيديوهات Pexels ---
    print(f"📽️ STEP 4: Fetching Videos for: {ai_data['search_term']}")
    headers_pex = {"Authorization": PEXELS_API}
    pex_url = f"https://api.pexels.com/videos/search?query={ai_data['search_term']}&per_page=5&orientation=portrait"
    vids = requests.get(pex_url, headers=headers_pex).json().get('videos', [])
    
    clips = []
    curr_d = 0
    for i, v in enumerate(vids):
        v_link = v['video_files'][0]['link']
        fname = f"v_{i}.mp4"
        with open(fname, "wb") as f: f.write(requests.get(v_link).content)
        c = VideoFileClip(fname).resized(height=1920).without_audio()
        clips.append(c)
        curr_d += c.duration
        if curr_d >= duration: break

    # --- الخطوة 5: المونتاج النهائي ---
    print("🎬 STEP 5: Rendering Video...")
    final_bg = concatenate_videoclips(clips)
    if final_bg.duration < duration:
        final_bg = concatenate_videoclips([final_bg] * (int(duration/final_bg.duration)+1))
    
    final_v = final_bg.subclipped(0, duration).with_audio(audio)
    final_v.write_videofile("final.mp4", fps=24, codec="libx264", audio_codec="aac")

    # --- الخطوة 6: الرفع لـ Dailymotion ---
    print("🚀 STEP 6: Uploading to Dailymotion...")
    auth = {"grant_type": "password", "client_id": DM_KEY, "client_secret": DM_SECRET, "username": DM_USER, "password": DM_PASS, "scope": "manage_videos"}
    r_auth = requests.post("https://api.dailymotion.com/oauth/token", data=auth)
    
    if r_auth.status_code == 200:
        token = r_auth.json().get("access_token")
        h_dm = {"Authorization": f"Bearer {token}"}
        
        # طلب رابط الرفع
        up_info = requests.get("https://api.dailymotion.com/file/upload", headers=h_dm).json()
        
        # الرفع الفعلي
        m = MultipartEncoder(fields={'file': ('final.mp4', open('final.mp4', 'rb'), 'video/mp4')})
        f_url = requests.post(up_info['upload_url'], data=m, headers={'Content-Type': m.content_type}).json()['url']
        
        # النشر النهائي
        requests.post("https://api.dailymotion.com/me/videos", headers=h_dm, data={
            "url": f_url,
            "title": ai_data['video_title'][:100],
            "description": f"{ai_data['script']}\n\n#news #trending {ai_data['tags']}",
            "tags": ai_data['tags'].replace("#", ""),
            "published": "true",
            "channel": "news"
        })
        
        # تحديث ملف التكرار
        with open("last_post.txt", "a") as f: f.write(title_trend + "\n")
        print("✅ SUCCESS: Trending video is live!")
    else:
        print(f"❌ DM Auth Error: {r_auth.text}")

if __name__ == "__main__":
    asyncio.run(main())
