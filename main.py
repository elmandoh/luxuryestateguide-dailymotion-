import feedparser, asyncio, edge_tts, requests, os, json
from groq import Groq
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips
from requests_toolbelt import MultipartEncoder

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
PEXELS_API = os.getenv("PEXELS_API")
DM_KEY = os.getenv("DM_API_KEY")
DM_SECRET = os.getenv("DM_API_SECRET")
DM_USER = os.getenv("DM_USER")
DM_PASS = os.getenv("DM_PASS")

# مصدر إخباري مستقر
NEWS_RSS = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"

async def main():
    print("🚀 Fetching News...")
    resp = requests.get(NEWS_RSS, headers={'User-Agent': 'Mozilla/5.0'})
    feed = feedparser.parse(resp.content)
    
    if not feed.entries: return

    processed = []
    if os.path.exists("last_post.txt"):
        with open("last_post.txt", "r") as f: processed = f.read().splitlines()

    target = next((e for e in feed.entries[:10] if e.title not in processed), None)
    if not target: return

    print(f"🌟 Story: {target.title}")

    # Groq AI
    try:
        completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": "Return ONLY JSON."},
                {"role": "user", "content": f"Script for: {target.title}. JSON: script, search, title, tags."}
            ],
            response_format={"type": "json_object"}
        )
        ai_data = json.loads(completion.choices[0].message.content)
    except Exception as e:
        print(f"Error: {e}"); return

    # Voice & Video
    v_path = "voice.mp3"
    await edge_tts.Communicate(ai_data['script'], "en-US-GuyNeural").save(v_path)
    audio = AudioFileClip(v_path)
    
    # Pexels & Rendering & Upload (باقي الكود المعتاد للرفع)
    # ... (الجزء ده ثابت زي ما بعتهولك المرة اللي فاتت)
    print("✅ Process Completed!")

if __name__ == "__main__":
    asyncio.run(main())
