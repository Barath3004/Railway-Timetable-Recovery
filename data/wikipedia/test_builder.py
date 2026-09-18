from station_builder import StationBuilder

builder = StationBuilder()

builder.add_wikipedia_data({
    "station_code": "MAS",
    "platforms_total": 17
})

builder.add_passenger_data({
    "daily_passengers": 730000
})

builder.add_timetable_data({
    "station_name": "MGR Chennai Central"
})

station = builder.build()

print(station)