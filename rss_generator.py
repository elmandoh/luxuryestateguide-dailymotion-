import json
from datetime import datetime

def generate_rss():
    try:
        with open('trends_raw.json', 'r', encoding='utf-8') as f:
            trends = json.load(f)

        # بداية هيكل ملف الـ RSS
        rss_items = ""
        for vid in trends:
            rss_items += f"""
        <item>
            <title><![CDATA[{vid['title']}]]></title>
            <link>{vid['url']}</link>
            <description><![CDATA[{vid['desc']}]]></description>
            <pubDate>{datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")}</pubDate>
            <guid isPermaLink="false">{vid['url']}</guid>
        </item>"""

        rss_feed = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
    <channel>
        <title>Dailymotion Trending RSS</title>
        <link>https://www.dailymotion.com</link>
        <description>أحدث فيديوهات التريند على ديلى موشن</description>
        <language>ar</language>
        {rss_items}
    </channel>
</rss>"""

        with open('dailymotion_feed.xml', 'w', encoding='utf-8') as f:
            f.write(rss_feed)
        return True
    except Exception as e:
        print(f"Error generating RSS: {e}")
        return False
