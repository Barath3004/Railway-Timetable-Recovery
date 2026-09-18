from wikipedia_mapper import WikipediaMapper

wiki = {

    "Station code": "MAS",

    "Station Name": "MGR Chennai Central",

    "Zone(s)": "Southern Railway zone",

    "Division(s)": "Chennai",

    "Platforms": "17 (12 main station + 5 Chennai Suburban Terminal)",

    "Electrified": "1931 ; 95 years ago (1931)"
}

mapper = WikipediaMapper(wiki)

result = mapper.map_all()

print(result)