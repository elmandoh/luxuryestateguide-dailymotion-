import requests
import os
from gtts import gTTS
from moviepy.editor import VideoFileClip, AudioFileClip

# 1️⃣ جلب موضوع تريند (مثال ثابت للتجربة)
def get_trending_topic():
    return "Artificial Intelligence"

# 2️⃣ توليد سكريبت باستخدام Groq
def generate_script(topic, groq_api_key):
    headers = {"Authorization": f"Bearer {groq_api_key}"}
    payload = {"prompt": f"اكتب سكريبت قصير عن {topic}"}
    response = requests.post("https://api.groq.com/v1/chat", headers=headers, json=payload)
    if response.status_code == 200:
        return response.json().get("text", f"هذا فيديو عن {topic}")
    return f"هذا فيديو عن {topic}"

# 3️⃣ تحويل النص إلى صوت
def text_to_speech(text, filename="voice.mp3"):
    tts = gTTS(text=text, lang="ar")
    tts.save(filename)
    return filename

# 4️⃣ جلب فيديو من Pexels
def get_video_from_pexels(query, pexels_api_key):
    headers = {"Authorization": pexels_api_key}
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=1"
    response = requests.get(url, headers=headers)
    data = response.json()
    video_url = data["videos"][0]["video_files"][0]["link"]
    video_file = "video.mp4"
    with requests.get(video_url, stream=True) as r:
        with open(video_file, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return video_file

# 5️⃣ دمج الصوت مع الفيديو
def merge_audio_video(video_file, audio_file, output_file="final.mp4"):
    video = VideoFileClip(video_file)
    audio = AudioFileClip(audio_file)
    final = video.set_audio(audio)
    final.write_videofile(output_file, codec="libx264", audio_codec="aac")
    return output_file

# 6️⃣ الحصول على Access Token من Dailymotion
def get_dm_token(api_key, api_secret, user, password):
    url = "https://api.dailymotion.com/oauth/token"
    data = {
        "grant_type": "password",
        "client_id": api_key,
        "client_secret": api_secret,
        "username": user,
        "password": password,
        "scope": "manage_videos"
    }
    response = requests.post(url, data=data)
    print("Token Response:", response.text)  # اطبع الرد علشان تتأكد
    return response.json().get("access_token")

# 7️⃣ رفع الفيديو على Dailymotion
def upload_to_dailymotion(video_file, token):
    url = "https://api.dailymotion.com/me/videos"
    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": open(video_file, "rb")}
    data = {
        "title": "فيديو تريند",
        "description": "فيديو مولد أوتوماتيكياً باستخدام Groq وPexels",
        "tags": "trend, ai, auto",
        "channel": "news",   # لازم تختار قناة مناسبة
        "published": "true",
        "private": "false"
    }
    response = requests.post(url, headers=headers, files=files, data=data)
    print("Dailymotion Response:", response.text)  # اطبع الرد كامل
    return response.json()

if __name__ == "__main__":
    groq_api_key = os.getenv("GROQ_API_KEY")
    pexels_api_key = os.getenv("PEXELS_API")
    dm_api_key = os.getenv("DM_API_KEY")
    dm_api_secret = os.getenv("DM_API_SECRET")
    dm_user = os.getenv("DM_USER")
    dm_pass = os.getenv("DM_PASS")

    topic = get_trending_topic()
    script = generate_script(topic, groq_api_key)
    audio_file = text_to_speech(script)
    video_file = get_video_from_pexels(topic, pexels_api_key)
    final_video = merge_audio_video(video_file, audio_file)

    token = get_dm_token(dm_api_key, dm_api_secret, dm_user, dm_pass)
    result = upload_to_dailymotion(final_video, token)
    print("Uploaded:", result)
