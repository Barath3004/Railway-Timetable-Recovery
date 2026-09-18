from wikipedia_downloader import WikipediaDownloader
from data.wikipedia.wikipedia_parser import WikipediaParser

URL = "https://en.wikipedia.org/wiki/Chennai_Central"

downloader = WikipediaDownloader()
parser = WikipediaParser()

html = downloader.download_page(URL)

info = parser.parse_infobox(html)

print("\n========== INFOBOX ==========\n")

for key, value in info.items():
    print(f"{key} : {value}")