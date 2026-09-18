from wikipedia_downloader import WikipediaDownloader

URL = "https://en.wikipedia.org/wiki/Chennai_Central"

downloader = WikipediaDownloader()

html = downloader.download_page(URL)

print()
print("=" * 50)
print("FIRST 500 CHARACTERS")
print("=" * 50)

print(html[:500])