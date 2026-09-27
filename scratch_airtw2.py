import urllib.request
from html.parser import HTMLParser

class MyHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_a = False
        self.current_href = ""
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.in_a = True
            for attr in attrs:
                if attr[0] == "href":
                    self.current_href = attr[1]

    def handle_endtag(self, tag):
        if tag == "a":
            self.in_a = False
            self.current_href = ""

    def handle_data(self, data):
        if self.in_a and self.current_href:
            if 'NewsId' in self.current_href or 'Details' in self.current_href:
                self.links.append((self.current_href, data.strip()))

url = "https://airtw.moenv.gov.tw/CHT/News.aspx"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    res = urllib.request.urlopen(req).read().decode('utf-8')
    parser = MyHTMLParser()
    parser.feed(res)
    print("Found news links:")
    for link, title in parser.links:
        if title:
            print(f"- {title} ({link})")
except Exception as e:
    print("Error:", e)
