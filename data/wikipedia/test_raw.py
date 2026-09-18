from data.wikipedia.wikipedia_downloader import WikipediaDownloader
from data.wikipedia.wikipedia_parser import WikipediaParser


url = "https://en.wikipedia.org/wiki/Perambur_railway_station"


downloader = WikipediaDownloader()
parser = WikipediaParser()


html = downloader.download_page(url)

data = parser.parse_infobox(html)


for key, value in data.items():
    print(key, ":", value)