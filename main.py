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

# مصدر الأخبار (Google News)
NEWS_RSS = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"

async def main():
    print("🚀 STEP 1: Fetching News...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(NEWS_RSS, headers=headers)
    feed = feedparser.parse(resp.content)
    
    if not feed.entries: 
        print("❌ No news entries found."); return

    # فحص التكرار لضمان عدم نشر نفس الخبر مرتين
    processed = []
    if os.path.exists("last_post.txt"):
        with open("last_post.txt", "r") as f: processed = f.read().splitlines()

    target = next((e for e in feed.entries[:10] if e.title not in processed), None)
    if not target: 
        print("⚠️ No new news found."); return

    print(f"🌟 Target Story: {target.title}")

# --- تحديث الخطوة 2 و 3 لمنع حدوث هذا الخطأ ---

    # STEP 2: Groq AI
    print("🤖 STEP 2: Generating 400-word Script...")
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Return ONLY JSON. Ensure the 'script' key contains the text."},
                {"role": "user", "content": f"Write a long viral news script (around 400 words) for: {target.title}. JSON keys: script, search, title, tags."}
            ],
            response_format={"type": "json_object"}
        )
        response_content = completion.choices[0].message.content
        ai_data = json.loads(response_content)
        
        # التأكد من أن النص موجود فعلاً وليس فارغاً
        if not ai_data.get('script'):
            raise ValueError("Script is empty in AI response")
            
    except Exception as e:
        print(f"❌ Groq Error or Invalid JSON: {e}")
        print(f"Full Response: {response_content}") # لتعرف ماذا أرسل الذكاء الاصطناعي بالضبط
        return

    # STEP 3: Voice Generation
    print("🎙️ STEP 3: Generating Voice...")
    v_path = "voice.mp3"
    script_text = str(ai_data['script']) # التأكد أن القيمة نصية
    
    try:
        communicate = edge_tts.Communicate(script_text, "en-US-GuyNeural")
        await communicate.save(v_path)
        audio = AudioFileClip(v_path)
    except Exception as e:
        print(f"❌ TTS Error: {e}")
        return

    # STEP 3: توليد التعليق الصوتي
    print("🎙️ STEP 3: Generating Long Voiceover...")
    v_path = "voice.mp3"
    # استخدام صوت Neural طبيعي
    await edge_tts.Communicate(ai_data['script'], "en-US-GuyNeural").save(v_path)
    audio = AudioFileClip(v_path)
    print(f"⏳ Audio Duration: {audio.duration:.2f} seconds")

    # STEP 4: جلب لقطات مكثفة من Pexels (20 لقطة لتغطية الـ 3 دقائق)
    print(f"📽️ STEP 4: Finding 20 Videos for {ai_data['search']}...")
    h_pex = {"Authorization": PEXELS_API}
    v_res = requests.get(f"https://api.pexels.com/videos/search?query={ai_data['search']}&per_page=20&orientation=portrait", headers=h_pex).json()
    
    clips = []
    for i, v in enumerate(v_res.get('videos', [])):
        try:
            v_url = v['video_files'][0]['link']
            v_temp = f"v{i}.mp4"
            with open(v_temp, "wb") as f: 
                f.write(requests.get(v_url).content)
            
            # معالجة الفيديو: تغيير الحجم وإزالة الصوت الأصلي
            clip = VideoFileClip(v_temp).resized(height=1920).without_audio()
            clips.append(clip)
            print(f"✅ Downloaded clip {i+1}")
        except Exception as e:
            print(f"⚠️ Skipping clip {i}: {e}")
            continue

    if not clips:
        print("❌ No videos found on Pexels."); return

    # STEP 5: المونتاج والرندرة (نسخة محسنة للفيديوهات الطويلة)
    print("🎬 STEP 5: Rendering Final 3-Minute Video...")
    final_bg = concatenate_videoclips(clips, method="compose")
    
    # تكرار الخلفية برمجياً حتى تغطي مدة الصوت بالكامل
    while final_bg.duration < audio.duration:
        final_bg = concatenate_videoclips([final_bg, final_bg])
    
    # دمج الصوت مع الفيديو وقصه عند نهاية الصوت
    final_v = final_bg.subclipped(0, audio.duration).with_audio(audio)
    
    # الرندرة باستخدام 4 خيوط معالجة (Threads) لتسريع العملية في GitHub
    final_v.write_videofile("final.mp4", fps=24, codec="libx264", audio_codec="aac", threads=4)

    # STEP 6: الرفع على Dailymotion
    print("🚀 STEP 6: Publishing to Dailymotion...")
    auth_data = {
        "grant_type": "password",
        "client_id": DM_KEY,
        "client_secret": DM_SECRET,
        "username": DM_USER,
        "password": DM_PASS,
        "scope": "manage_videos"
    }
    
    try:
        token_resp = requests.post("https://api.dailymotion.com/oauth/token", data=auth_data).json()
        token = token_resp.get("access_token")
        
        if token:
            # 1. الحصول على رابط الرفع
            up_url = requests.get("https://api.dailymotion.com/file/upload", 
                                  headers={"Authorization": f"Bearer {token}"}).json()['upload_url']
            
            # 2. رفع الملف
            m = MultipartEncoder(fields={'file': ('final.mp4', open('final.mp4', 'rb'), 'video/mp4')})
            f_url = requests.post(up_url, data=m, headers={'Content-Type': m.content_type}).json()['url']
            
            # 3. إنشاء الفيديو ونشره
            create_v = requests.post("https://api.dailymotion.com/me/videos", 
                                     headers={"Authorization": f"Bearer {token}"}, 
                                     data={
                                         "url": f_url,
                                         "title": ai_data['title'][:100],
                                         "description": ai_data['script'][:5000], # الوصف الطويل مفيد للـ SEO
                                         "published": "true",
                                         "channel": "news",
                                         "is_created_for_kids": "false",
                                         "tags": ai_data['tags']
                                     }).json()
            
            if "id" in create_v:
                print(f"✅ SUCCESS! Video Link: https://www.dailymotion.com/video/{create_v['id']}")
                with open("last_post.txt", "a") as f: f.write(target.title + "\n")
            else:
                print(f"❌ Publish Error: {create_v}")
        else:
            print(f"❌ Auth Failed: {token_resp}")
    except Exception as e:
        print(f"❌ Upload Process Error: {e}")

    # تنظيف الملفات المؤقتة لتوفير مساحة في GitHub Runner
    print("🧹 Cleaning up temporary files...")
    for file in [f"v{i}.mp4" for i in range(len(clips))] + ["voice.mp3", "final.mp4"]:
        if os.path.exists(file): os.remove(file)

if __name__ == "__main__":
    asyncio.run(main())
