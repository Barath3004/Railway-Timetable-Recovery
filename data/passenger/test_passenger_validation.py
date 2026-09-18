from data.passenger.passenger_builder import PassengerBuilder


def main():

    builder = PassengerBuilder()


    builder.process_division(
        "data/raw/madurai_division.pdf",
        "Madurai"
    )


    builder.process_division(
        "data/raw/thiruvananthapuram_division.pdf",
        "Thiruvananthapuram"
    )


    builder.process_division(
        "data/raw/chennai_division.pdf",
        "Chennai"
    )


    records = builder.build()


    print("\n")
    print("="*60)
    print("PASSENGER DATA VALIDATION")
    print("="*60)


    print(
        "Total Records:",
        len(records)
    )


    empty_names = [
        r for r in records
        if not r["station_name"]
    ]

    empty_codes = [
        r for r in records
        if not r["station_code"]
    ]


    print(
        "Empty Station Names:",
        len(empty_names)
    )


    print(
        "Empty Station Codes:",
        len(empty_codes)
    )


    categories = {}

    for r in records:

        cat = r["category"]

        categories[cat] = categories.get(cat,0)+1


    print("\nCATEGORY COUNT")

    for key,value in sorted(categories.items()):

        print(
            key,
            ":",
            value
        )


    divisions={}

    for r in records:

        div=r["division"]

        divisions[div]=divisions.get(div,0)+1


    print("\nDIVISION COUNT")

    for key,value in divisions.items():

        print(
            key,
            ":",
            value
        )



if __name__=="__main__":
    main()