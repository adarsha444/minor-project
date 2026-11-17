import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'weather_data.db')

def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weather_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT NOT NULL,
                country TEXT NOT NULL,
                temperature REAL NOT NULL,
                humidity REAL NOT NULL,
                pressure REAL NOT NULL,
                wind_speed REAL NOT NULL,
                clouds REAL NOT NULL,
                rain_prediction TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_city ON weather_data(city)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON weather_data(timestamp)')
        
        conn.commit()
        conn.close()
        print("[OK] SQLite database initialized successfully at:", DB_PATH)
    except Exception as e:
        print(f"[ERROR] Error initializing database: {str(e)}")
        raise

def save_weather_data(city, country, temperature, humidity, pressure, wind_speed, clouds, rain_prediction):
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        conn.isolation_level = None  # Autocommit mode
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO weather_data (city, country, temperature, humidity, pressure, wind_speed, clouds, rain_prediction)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (city, country, temperature, humidity, pressure, wind_speed, clouds, rain_prediction))
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving weather data: {str(e)}")
        return False

def get_weather_history(city=None, limit=50):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if city:
            cursor.execute('''
                SELECT * FROM weather_data WHERE city = ? ORDER BY timestamp DESC LIMIT ?
            ''', (city, limit))
        else:
            cursor.execute('''
                SELECT * FROM weather_data ORDER BY timestamp DESC LIMIT ?
            ''', (limit,))
        
        rows = cursor.fetchall()
        records = []
        for row in rows:
            records.append({
                'id': row['id'],
                'city': row['city'],
                'country': row['country'],
                'temperature': row['temperature'],
                'humidity': row['humidity'],
                'pressure': row['pressure'],
                'wind_speed': row['wind_speed'],
                'clouds': row['clouds'],
                'rain_prediction': row['rain_prediction'],
                'timestamp': row['timestamp']
            })
        conn.close()
        return records
    except Exception as e:
        print(f"Error retrieving weather history: {str(e)}")
        return []

def get_all_cities():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT city FROM weather_data ORDER BY city')
        rows = cursor.fetchall()
        cities = [row[0] for row in rows]
        conn.close()
        return cities
    except Exception as e:
        print(f"Error retrieving cities: {str(e)}")
        return []

def clear_weather_data():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM weather_data')
        conn.commit()
        conn.close()

        conn_vacuum = sqlite3.connect(DB_PATH)
        cursor_vacuum = conn_vacuum.cursor()
        cursor_vacuum.execute('VACUUM')
        conn_vacuum.close()

        return True
    except Exception as e:
        print(f"Error clearing weather data: {str(e)}")
        return False


def get_city_stats(city):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT temperature, humidity FROM weather_data WHERE city = ? ORDER BY timestamp DESC
        ''', (city,))
        rows = cursor.fetchall()
        
        if not rows:
            conn.close()
            return None
        
        temps = [row['temperature'] for row in rows]
        humidities = [row['humidity'] for row in rows]
        
        cursor.execute('''
            SELECT * FROM weather_data WHERE city = ? ORDER BY timestamp DESC LIMIT 1
        ''', (city,))
        latest = cursor.fetchone()
        
        conn.close()
        
        stats = {
            'city': city,
            'total_records': len(rows),
            'avg_temp': round(sum(temps) / len(temps), 2),
            'min_temp': round(min(temps), 2),
            'max_temp': round(max(temps), 2),
            'avg_humidity': round(sum(humidities) / len(humidities), 2),
            'latest_record': {
                'id': latest['id'],
                'city': latest['city'],
                'country': latest['country'],
                'temperature': latest['temperature'],
                'humidity': latest['humidity'],
                'pressure': latest['pressure'],
                'wind_speed': latest['wind_speed'],
                'clouds': latest['clouds'],
                'rain_prediction': latest['rain_prediction'],
                'timestamp': latest['timestamp']
            }
        }
        return stats
    except Exception as e:
        print(f"Error retrieving city stats: {str(e)}")
        return None



