"""
Test Passenger Builder
"""


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
    print("=" * 60)
    print("FINAL PASSENGER DATASET")
    print("=" * 60)


    print(
        "Total Stations :",
        len(records)
    )


    print("\nFIRST 10 RECORDS\n")


    for record in records[:10]:

        print(record)



if __name__ == "__main__":
    main()