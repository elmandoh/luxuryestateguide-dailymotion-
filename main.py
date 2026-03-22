import feedparser, asyncio, edge_tts, requests, os, re
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips
from requests_toolbelt import MultipartEncoder

# الإعدادات الأساسية
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PEXELS_API = os.getenv("PEXELS_API")
DM_KEY = os.getenv("DM_API_KEY")
DM_SECRET = os.getenv("DM_API_SECRET")
DM_USER = os.getenv("DM_USER")
DM_PASS = os.getenv("DM_PASS")

# رابط تريندات جوجل (Global/US لجلب أعلى بحث)
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
    print("🔥 Analyzing Google Hot Trends via Groq...")
    feed = feedparser.parse(TRENDS_RSS)
    if not feed.entries: return
    
    top_trend = feed.entries[0].title
    print(f"🌟 Top Trend Found: {top_trend}")

    # منع التكرار
    if os.path.exists("last_post.txt"):
        with open("last_post.txt", "r") as f:
            if f.read().strip() == top_trend:
                print("⚠️ Already processed this trend.")
                return

    # طلب السكريبت والتفاصيل من Groq (بصيغة JSON)
    prompt = f"""
    Create a viral short video content about the trend '{top_trend}'.
    Return JSON format with: 
    'script': (max 40 words, engaging),
    'search_term': (best 1-word search for Pexels videos),
    'title': (viral title with emojis),
    'tags': (5 relevant hashtags)
    """
    ai_data = eval(ask_groq(prompt)) # تحويل النص لـ Dictionary
    
    # 1. توليد الصوت
    voice_path = "voice.mp3"
    await edge_tts.Communicate(ai_data['script'], "en-US-GuyNeural").save(voice_path)
    audio = AudioFileClip(voice_path)
    duration = audio.duration

    # 2. جلب فيديوهات Pexels بناءً على ترشيح Groq
    print(f"🎬 Searching Pexels for: {ai_data['search_term']}")
    headers = {"Authorization": PEXELS_API}
    pex_res = requests.get(f"https://api.pexels.com/videos/search?query={ai_data['search_term']}&per_page=5&orientation=portrait", headers=headers).json()
    
    clips = []
    curr_d = 0
    for i, v in enumerate(pex_res.get('videos', [])):
        v_url = v['video_files'][0]['link']
        temp = f"v_{i}.mp4"
        with open(temp, "wb") as f: f.write(requests.get(v_url).content)
        c = VideoFileClip(temp).resized(height=1920).without_audio()
        clips.append(c)
        curr_d += c.duration
        if curr_d >= duration: break

    # 3. مونتاج الفيديو
    final_bg = concatenate_videoclips(clips)
    if final_bg.duration < duration:
        final_bg = concatenate_videoclips([final_bg] * (int(duration/final_bg.duration)+1))
    
    final_video = final_bg.subclipped(0, duration).with_audio(audio)
    final_video.write_videofile("final.mp4", fps=24, codec="libx264", audio_codec="aac")

    # 4. الرفع لـ Dailymotion
    # (استخدم نفس كود الرفع السابق مع استخدام ai_data['title'] و ai_data['tags'])
    print(f"🚀 Uploading: {ai_data['title']}")
    # ... (كود الرفع هنا) ...

    with open("last_post.txt", "w") as f: f.write(top_trend)
    print("✅ Viral Trend Video is Live!")

if __name__ == "__main__":
    asyncio.run(main())
