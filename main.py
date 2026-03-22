import requests
import os
import time
from gtts import gTTS
from moviepy.editor import VideoFileClip, AudioFileClip
# استيراد متوافق مع moviepy 2.x
# استيراد متوافق مع moviepy 2.x
try:
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.audio.io.AudioFileClip import AudioFileClip
except Exception as e:
    print("moviepy import fallback failed:", e)
    raise



# جلب تريند من Google Trends TV
def get_trending_topic():
    try:
        url = "https://trends.google.com/trends/hottrends/visualize/internal/data"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        # مرونة: حاول استخراج أول تريند من أي شكل للـ JSON
        if isinstance(data, list) and len(data) > 0:
            first = data[0]
            if isinstance(first, list) and len(first) > 0:
                return str(first[0])
            if isinstance(first, dict):
                # بعض الصيغ تحتوي على key مثل "title" أو "news"
                for k in ("title","news","query"):
                    if k in first:
                        return str(first[k])
        return "Trending"
    except Exception as e:
        print("Error fetching trends:", e)
        return "Trending"

# اختيار القناة حسب الموضوع
def choose_channel(topic):
    t = topic.lower()
    if any(k in t for k in ["news","حدث","سياسة","breaking"]):
        return "news"
    if any(k in t for k in ["ai","tech","تكنولوجيا","ذكاء"]):
        return "tech"
    if any(k in t for k in ["sport","كرة","رياضة"]):
        return "sports"
    if any(k in t for k in ["music","أغنية","song"]):
        return "music"
    if any(k in t for k in ["game","gaming","لعبة"]):
        return "gaming"
    if any(k in t for k in ["animal","حيوان","nature"]):
        return "animals"
    if any(k in t for k in ["car","سيارة","auto"]):
        return "auto"
    return "people"

# توليد سكريبت (fallback نصي لو Groq يفشل)
def generate_script(topic, groq_api_key):
    try:
        if not groq_api_key:
            return f"هذا فيديو عن {topic}"
        headers = {"Authorization": f"Bearer {groq_api_key}"}
        payload = {"prompt": f"اكتب سكريبت قصير ومباشر بالعربية عن {topic}"}
        r = requests.post("https://api.groq.com/v1/chat", headers=headers, json=payload, timeout=15)
        r.raise_for_status()
        j = r.json()
        return j.get("text") or j.get("message") or f"هذا فيديو عن {topic}"
    except Exception as e:
        print("Groq error:", e)
        return f"هذا فيديو عن {topic}"

# تحويل النص إلى صوت
def text_to_speech(text, filename="voice.mp3"):
    tts = gTTS(text=text, lang="ar")
    tts.save(filename)
    return filename

# جلب فيديو من Pexels مع فحص وجود نتائج
def get_video_from_pexels(query, pexels_api_key):
    try:
        headers = {"Authorization": pexels_api_key}
        url = f"https://api.pexels.com/videos/search?query={requests.utils.requote_uri(query)}&per_page=1"
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        videos = data.get("videos") or []
        if not videos:
            raise ValueError("No videos found")
        video_url = videos[0]["video_files"][0]["link"]
        video_file = "video.mp4"
        with requests.get(video_url, stream=True, timeout=30) as resp:
            resp.raise_for_status()
            with open(video_file, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return video_file
    except Exception as e:
        print("Pexels error or no video:", e)
        # fallback: استخدم ملف فيديو محلي إن وُجد أو ارجع خطأ واضح
        if os.path.exists("fallback.mp4"):
            return "fallback.mp4"
        raise

# دمج الصوت مع الفيديو
def merge_audio_video(video_file, audio_file, output_file="final.mp4"):
    try:
        video = VideoFileClip(video_file)
        audio = AudioFileClip(audio_file)
        final = video.set_audio(audio)
        final.write_videofile(output_file, codec="libx264", audio_codec="aac", verbose=False, logger=None)
        video.close(); audio.close()
        return output_file
    except Exception as e:
        print("Merge error:", e)
        raise

# الحصول على Access Token من Dailymotion
def get_dm_token(api_key, api_secret, user, password):
    try:
        url = "https://api.dailymotion.com/oauth/token"
        data = {
            "grant_type": "password",
            "client_id": api_key,
            "client_secret": api_secret,
            "username": user,
            "password": password,
            "scope": "manage_videos"
        }
        r = requests.post(url, data=data, timeout=15)
        r.raise_for_status()
        print("Token Response:", r.text)
        return r.json().get("access_token")
    except Exception as e:
        print("Token fetch error:", e)
        return None

# رفع الفيديو على Dailymotion
def upload_to_dailymotion(video_file, token, topic, channel):
    try:
        url = "https://api.dailymotion.com/me/videos"
        headers = {"Authorization": f"Bearer {token}"}
        files = {"file": open(video_file, "rb")}
        data = {
            "title": f"فيديو تريند: {topic}",
            "description": f"فيديو مولد أوتوماتيكياً عن {topic}",
            "tags": f"trend,{topic}",
            "channel": channel,
            "published": "true",
            "private": "false"
        }
        r = requests.post(url, headers=headers, files=files, data=data, timeout=60)
        print("Upload response:", r.status_code, r.text)
        return r.json()
    except Exception as e:
        print("Upload error:", e)
        raise
    finally:
        try:
            files["file"].close()
        except:
            pass

# تعديل ميتاداتا الفيديو بعد الرفع لو احتاج
def update_video_metadata(video_id, token, title, description, channel):
    try:
        url = f"https://api.dailymotion.com/video/{video_id}"
        headers = {"Authorization": f"Bearer {token}"}
        data = {
            "title": title,
            "description": description,
            "channel": channel,
            "published": "true",
            "private": "false"
        }
        r = requests.patch(url, headers=headers, data=data, timeout=15)
        print("Update response:", r.status_code, r.text)
        return r.json()
    except Exception as e:
        print("Update error:", e)
        return None

if __name__ == "__main__":
    # احصل على المتغيرات من Secrets في GitHub Actions
    groq_api_key = os.getenv("GROQ_API_KEY")
    pexels_api_key = os.getenv("PEXELS_API")
    dm_api_key = os.getenv("DM_API_KEY")
    dm_api_secret = os.getenv("DM_API_SECRET")
    dm_user = os.getenv("DM_USER")
    dm_pass = os.getenv("DM_PASS")

    topic = get_trending_topic()
    print("Selected Trend:", topic)

    script = generate_script(topic, groq_api_key)
    print("Script preview:", script[:200])

    audio_file = text_to_speech(script)
    print("Audio saved:", audio_file)

    try:
        video_file = get_video_from_pexels(topic, pexels_api_key)
        print("Video downloaded:", video_file)
    except Exception:
        print("No Pexels video found, aborting.")
        raise

    final_video = merge_audio_video(video_file, audio_file)
    print("Final video created:", final_video)

    token = get_dm_token(dm_api_key, dm_api_secret, dm_user, dm_pass)
    if not token:
        print("No token, aborting upload.")
        raise SystemExit(1)

    channel = choose_channel(topic)
    upload_resp = upload_to_dailymotion(final_video, token, topic, channel)
    print("Upload result:", upload_resp)

    # لو العنوان فاضي أو الفيديو غير منشور، نعمل تحديث تلقائي
    video_id = upload_resp.get("id") or upload_resp.get("video_id")
    if video_id:
        # تحقق من الحقول في الرد
        title = upload_resp.get("title") or f"فيديو تريند: {topic}"
        published = upload_resp.get("published")
        if not title or published is False:
            print("Fixing metadata via PATCH...")
            update_video_metadata(video_id, token, title, f"فيديو مولد أوتوماتيكياً عن {topic}", channel)
        # اطبع رابط الفيديو لو موجود
        url = upload_resp.get("url") or f"https://www.dailymotion.com/video/{video_id}"
        print("Final video URL:", url)
    else:
        print("No video id returned from upload.")
