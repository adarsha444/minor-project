from database import get_weather_history, get_all_cities
import sys

def display_database():
    print("\n" + "="*110)
    print("WEATHER DATABASE VIEWER")
    print("="*110 + "\n")
    
    # Get all cities
    cities = get_all_cities()
    
    if not cities:
        print(" No data found in database. The database is empty.")
        return
    
    print(f" Available cities: {', '.join(cities)}\n")
    
    # Get all weather history
    data = get_weather_history(limit=100)
    
    if not data:
        print(" No records found in database.")
        return
    
    print(f"📊 Showing {len(data)} most recent records\n")
    
    # Print header
    print(f"{'City':<15} {'Country':<12} {'Temp':<8} {'Humidity':<10} {'Pressure':<12} {'Wind':<8} {'Clouds':<8} {'Rain':<10} {'Timestamp':<19}")
    print("-" * 110)
    
    # Print data rows
    for record in data:
        print(f"{record['city']:<15} {record['country']:<12} {record['temperature']:>6.1f}°C {record['humidity']:>8.0f}% {record['pressure']:>10.0f} hPa {record['wind_speed']:>6.1f}m/s {record['clouds']:>6.0f}% {record['rain_prediction']:<10} {record['timestamp']:<19}")
    
    print("-" * 110)
    print("="*110 + "\n")

def display_city_data(city):
    print("\n" + "="*110)
    print(f"WEATHER DATA FOR {city.upper()}")
    print("="*110 + "\n")
    
    # Get city-specific weather history
    data = get_weather_history(city=city, limit=50)
    
    if not data:
        print(f"❌ No records found for city: {city}")
        return
    
    print(f"📊 Showing {len(data)} records for {city}\n")
    
    # Print header
    print(f"{'Country':<12} {'Temp':<8} {'Humidity':<10} {'Pressure':<12} {'Wind':<8} {'Clouds':<8} {'Rain':<10} {'Timestamp':<19}")
    print("-" * 110)
    
    # Print data rows
    for record in data:
        print(f"{record['country']:<12} {record['temperature']:>6.1f}°C {record['humidity']:>8.0f}% {record['pressure']:>10.0f} hPa {record['wind_speed']:>6.1f}m/s {record['clouds']:>6.0f}% {record['rain_prediction']:<10} {record['timestamp']:<19}")
    
    print("-" * 110)
    print("="*110 + "\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Display data for a specific city
        city = sys.argv[1]
        display_city_data(city)
    else:
        # Display all data
        display_database()
