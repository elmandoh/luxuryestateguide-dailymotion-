import feedparser, asyncio, edge_tts, requests, os, json
from groq import Groq
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- الإعدادات من GitHub Secrets ---
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
PEXELS_API = os.getenv("PEXELS_API")
# توكن اليوتيوب المشفر (هنطلعه سوا)
YOUTUBE_TOKEN_DATA = os.getenv("YOUTUBE_TOKEN_JSON") 

NEWS_RSS = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"

async def generate_video():
    print("🚀 STEP 1: Fetching News...")
    resp = requests.get(NEWS_RSS, headers={'User-Agent': 'Mozilla/5.0'})
    feed = feedparser.parse(resp.content)
    
    if not feed.entries: return None, None, None

    # فحص التكرار (ملف منفصل لليوتيوب)
    processed = []
    if os.path.exists("yt_last_post.txt"):
        with open("yt_last_post.txt", "r") as f: processed = f.read().splitlines()

    target = next((e for e in feed.entries[:10] if e.title not in processed), None)
    if not target: 
        print("⚠️ No new news for YouTube."); return None, None, None

    print(f"🌟 Story: {target.title}")

    # STEP 2: Groq AI
    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "Return ONLY JSON."},
            {"role": "user", "content": f"Create viral Shorts script (30 words) and 1 search keyword for: {target.title}. JSON: script, search, title."}
        ],
        response_format={"type": "json_object"}
    )
    ai_data = json.loads(completion.choices[0].message.content)

    # STEP 3: Voice Generation
    v_path = "yt_voice.mp3"
    await edge_tts.Communicate(ai_data['script'], "en-US-GuyNeural").save(v_path)
    audio = AudioFileClip(v_path)

    # STEP 4: Pexels Videos
    print(f"📽️ Finding clips for: {ai_data['search']}...")
    h_pex = {"Authorization": PEXELS_API}
    v_res = requests.get(f"https://api.pexels.com/videos/search?query={ai_data['search']}&per_page=3&orientation=portrait", headers=h_pex).json()
    
    clips = []
    for i, v in enumerate(v_res.get('videos', [])):
        v_url = v['video_files'][0]['link']
        with open(f"yt_v{i}.mp4", "wb") as f: f.write(requests.get(v_url).content)
        clip = VideoFileClip(f"yt_v{i}.mp4").resized(height=1920).without_audio()
        clips.append(clip)

    if not clips: return None, None, None

    # STEP 5: Rendering
    final_bg = concatenate_videoclips(clips)
    if final_bg.duration < audio.duration: 
        final_bg = concatenate_videoclips([final_bg]*2)
    
    final_v = final_bg.subclipped(0, audio.duration).with_audio(audio)
    final_v.write_videofile("yt_final.mp4", fps=24, codec="libx264")
    
    return "yt_final.mp4", ai_data['title'], ai_data['script'], target.title

def upload_to_youtube(video_path, title, script):
    print("📤 STEP 6: Uploading to YouTube...")
    try:
        creds = Credentials.from_authorized_user_info(json.loads(YOUTUBE_TOKEN_DATA))
        youtube = build("youtube", "v3", credentials=creds)

        body = {
            'snippet': {
                'title': title[:100],
                'description': f"{script}\n\n#shorts #news #trending",
                'categoryId': '25'
            },
            'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
        }

        insert_request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True)
        )
        response = insert_request.execute()
        print(f"✅ YouTube Upload Success! ID: {response['id']}")
        return True
    except Exception as e:
        print(f"❌ YouTube Upload Failed: {e}")
        return False

async def main():
    video_file, title, script, original_title = await generate_video()
    if video_file:
        success = upload_to_youtube(video_file, title, script)
        if success:
            with open("yt_last_post.txt", "a") as f: f.write(original_title + "\n")

if __name__ == "__main__":
    asyncio.run(main())
