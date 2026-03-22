import requests
import json
from gtts import gTTS
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
import os

# 1️⃣ جلب التريندات من Google Trends API (مثال مبسط)
def get_trending_topic():
    # هنا ممكن تستخدم Google Trends API أو أي مصدر تريندات
    # للتجربة هنرجع كلمة ثابتة
    return "Artificial Intelligence"

# 2️⃣ توليد نص باستخدام Groq
def generate_script(topic, groq_api_key):
    headers = {"Authorization": f"Bearer {groq_api_key}"}
    payload = {"prompt": f"اكتب سكريبت قصير عن {topic}"}
    # مثال مبسط، لازم تعدل حسب API الحقيقي
    response = requests.post("https://api.groq.com/v1/chat", headers=headers, json=payload)
    return response.json().get("text", f"هذا فيديو عن {topic}")

# 3️⃣ تحويل النص إلى صوت
def text_to_speech(text, filename="voice.mp3"):
    tts = gTTS(text=text, lang="ar")
    tts.save(filename)
    return filename

# 4️⃣ جلب فيديو من Pexels API
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

# 6️⃣ رفع الفيديو على Dailymotion
def upload_to_dailymotion(video_file, access_token):
    url = "https://api.dailymotion.com/me/videos"
    headers = {"Authorization": f"Bearer {access_token}"}
    files = {"file": open(video_file, "rb")}
    data = {"title": "فيديو تريند", "published": "true"}
    response = requests.post(url, headers=headers, files=files, data=data)
    return response.json()

if __name__ == "__main__":
    groq_api_key = os.getenv("GROQ_API_KEY")
    pexels_api_key = os.getenv("PEXELS_API_KEY")
    dailymotion_token = os.getenv("DAILYMOTION_ACCESS_TOKEN")

    topic = get_trending_topic()
    script = generate_script(topic, groq_api_key)
    audio_file = text_to_speech(script)
    video_file = get_video_from_pexels(topic, pexels_api_key)
    final_video = merge_audio_video(video_file, audio_file)
    result = upload_to_dailymotion(final_video, dailymotion_token)
    print("Uploaded:", result)
