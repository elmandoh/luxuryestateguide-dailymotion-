import json
import google.generativeai as genai

# حط الـ API Key بتاعك هنا
genai.configure(api_key="YOUR_GEMINI_API_KEY")

def generate_reels_scripts():
    try:
        with open('trends_raw.json', 'r', encoding='utf-8') as f:
            trends = json.load(f)

        model = genai.GenerativeModel('gemini-1.5-flash')
        
        scripts_output = []
        for vid in trends:
            prompt = f"حلل هذا الفيديو الرائج: {vid['title']}. الوصف: {vid['desc']}. اكتب لي سكريبت فيديو Reels قصير (30 ثانية) باللغة العربية يتحدث عن هذا الموضوع بشكل جذاب."
            
            response = model.generate_content(prompt)
            scripts_output.append({
                "original_title": vid['title'],
                "ai_script": response.text,
                "url": vid['url']
            })

        with open('reels_scripts.json', 'w', encoding='utf-8') as f:
            json.dump(scripts_output, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Error in Summarizer: {e}")
        return False
