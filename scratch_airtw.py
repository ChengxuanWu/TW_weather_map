import urllib.request
import re

url = "https://airtw.moenv.gov.tw/CHT/AirNews.aspx"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    res = urllib.request.urlopen(req).read().decode('utf-8')
    matches = re.findall(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>', res)
    news = [(link, title.strip()) for link, title in matches if 'Details' in link or 'News' in link]
    print("Found news links:")
    for link, title in news[:10]:
        print(f"- {title} ({link})")
except Exception as e:
    print("Error:", e)
