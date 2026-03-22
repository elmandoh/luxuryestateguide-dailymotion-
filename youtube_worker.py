import os
import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# الإعدادات
CLIENT_SECRETS_FILE = "client_secrets.json"
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_authenticated_service():
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, SCOPES)
    # في أول مرة هيحتاج تدخل وتوافق، وبعد كدة بنستخدم Token
    credentials = flow.run_local_server(port=0)
    return build("youtube", "v3", credentials=credentials)

def upload_video(youtube, file_path, title, description):
    body = {
        'snippet': {
            'title': title[:100],
            'description': description,
            'tags': ['shorts', 'news', 'trending'],
            'categoryId': '25' # فئة الأخبار
        },
        'status': {
            'privacyStatus': 'public', # هينزل عام فوراً
            'selfDeclaredMadeForKids': False,
        }
    }

    insert_request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=MediaFileUpload(file_path, chunksize=-1, resumable=True)
    )

    response = insert_request.execute()
    print(f"✅ Video uploaded! ID: {response['id']}")

# هنا هتدمج خطوات الـ AI والرندرة اللي عملناها في main.py
# وفي الآخر تنادي دالة upload_video("final.mp4", ai_title, ai_script)
