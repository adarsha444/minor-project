from database import clear_weather_data


def clear_database():
    print("\n" + "=" * 60)
    print("CLEAR WEATHER DATABASE")
    print("=" * 60 + "\n")

    success = clear_weather_data()

    if success:
        print(" All weather records have been cleared from the database.")
    else:
        print(" Failed to clear the weather database. Check that the database file is accessible and not locked.")

    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    clear_database()
