from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pickle
import numpy as np
import os
import logging
import requests
import threading
from database import init_db, save_weather_data, get_weather_history, get_all_cities, get_city_stats, clear_weather_data

app = Flask(__name__, static_folder=os.path.dirname(__file__), static_url_path='')

init_db()

CORS(app)

@app.route('/')
def index():
    return send_file('index.html')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PORT = 5000

OPENWEATHER_API_KEY = '391a18f93943c84aa96c8a25ea89c991'
OPENWEATHER_BASE_URL = 'https://api.openweathermap.org/data/2.5/weather'
OPENWEATHER_FORECAST_URL = 'https://api.openweathermap.org/data/2.5/forecast'

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'rainfall_model.pkl')

PREDICTION_FEATURE_ORDER = [
    'tempmax', 'tempmin', 'temp', 'dew', 'humidity', 'windgust',
    'windspeed', 'winddir', 'sealevelpressure', 'cloudcover',
    'visibility', 'solarradiation', 'month', 'day_of_year',
    'rainfall_lag_1', 'rainfall_lag_3', 'rainfall_lag_7',
    'rainfall_avg_3', 'rainfall_avg_7'
]

model = None

def load_model():
    global model
    try:
        if not os.path.exists(MODEL_PATH):
            logger.error(f"Model file not found at {MODEL_PATH}")
            logger.warning("Using dummy model for testing")
            return None

        with open(MODEL_PATH, 'rb') as f:
            model = pickle.load(f)

        logger.info(f"ML model loaded successfully from {MODEL_PATH}")
        logger.info(f"Loaded model type: {type(model)}")
        return model
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}")
        return None

load_model()

def predict_rainfall(features):
    try:
        if all(field in features for field in PREDICTION_FEATURE_ORDER):
            feature_array = np.array([features[field] for field in PREDICTION_FEATURE_ORDER]).reshape(1, -1)
        elif model is not None and hasattr(model, 'num_feature') and model.num_feature() == 5:
            if all(field in features for field in ['temperature', 'humidity', 'pressure', 'wind_speed', 'clouds']):
                feature_array = np.array([
                    features['temperature'],
                    features['humidity'],
                    features['pressure'],
                    features['wind_speed'],
                    features['clouds']
                ]).reshape(1, -1)
            elif all(field in features for field in ['temp', 'humidity', 'sealevelpressure', 'windspeed', 'cloudcover']):
                feature_array = np.array([
                    features['temp'],
                    features['humidity'],
                    features['sealevelpressure'],
                    features['windspeed'],
                    features['cloudcover']
                ]).reshape(1, -1)
            else:
                missing = [field for field in ['temperature', 'humidity', 'pressure', 'wind_speed', 'clouds'] if field not in features]
                raise KeyError(f'Missing required fallback prediction fields: {", ".join(missing)}')
        else:
            missing = [field for field in PREDICTION_FEATURE_ORDER if field not in features]
            raise KeyError(f'Missing required prediction fields: {", ".join(missing)}')

        logger.info(f"Features for prediction: {feature_array}")

        if model is None:
            logger.warning("Using dummy prediction logic")
            if 'humidity' in features and 'cloudcover' in features:
                return "Yes" if features['humidity'] > 70 and features['cloudcover'] > 50 else "No"
            return "No"

        raw_pred = model.predict(feature_array)

        if isinstance(raw_pred, (list, tuple, np.ndarray)):
            raw_value = np.array(raw_pred).flatten()[0]
        else:
            raw_value = raw_pred

        if isinstance(raw_value, (float, np.floating)):
            prediction = 1 if raw_value >= 0.5 else 0
        elif isinstance(raw_value, (int, np.integer)):
            prediction = int(raw_value)
        else:
            prediction = 1 if str(raw_value).strip().lower() in ('yes', 'true', '1') else 0

        result = "Yes" if prediction == 1 else "No"
        logger.info(f"Prediction result: {result}")

        return result
    except Exception as e:
        logger.error(f"Error during prediction: {str(e)}")
        raise

def _derive_api_rain_prediction(weather_item):
    try:
        weather_desc = ''
        if 'weather' in weather_item and weather_item['weather']:
            weather_desc = weather_item['weather'][0].get('description', '').lower()

        pop = float(weather_item.get('pop', 0)) if weather_item.get('pop', 0) is not None else 0
        if 'rain' in weather_desc or 'thunderstorm' in weather_desc or pop > 0.4:
            return 'Yes'
        return 'No'
    except Exception:
        return 'No'


def parse_date_field(date_value):
    from datetime import datetime

    if isinstance(date_value, str):
        try:
            return datetime.fromisoformat(date_value)
        except ValueError:
            for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y'):
                try:
                    return datetime.strptime(date_value, fmt)
                except ValueError:
                    continue
            raise ValueError('Unsupported date format. Use ISO format or YYYY-MM-DD.')

    raise ValueError('Date must be a string in ISO or YYYY-MM-DD format.')


def extract_prediction_features(data):
    feature_data = data.copy()

    if 'month' not in feature_data or 'day_of_year' not in feature_data:
        if 'date' not in feature_data:
            raise ValueError('Either provide month/day_of_year or a date field.')

        dt = parse_date_field(feature_data['date'])
        feature_data.setdefault('month', dt.month)
        feature_data.setdefault('day_of_year', dt.timetuple().tm_yday)

    missing = [field for field in PREDICTION_FEATURE_ORDER if field not in feature_data]
    if missing:
        raise KeyError(f'Missing required prediction fields: {", ".join(missing)}')

    extracted = {}
    for field in PREDICTION_FEATURE_ORDER:
        value = feature_data[field]
        if value is None or value == '':
            raise ValueError(f'Value for {field} is required and cannot be empty.')
        try:
            extracted[field] = float(value)
        except (ValueError, TypeError):
            raise ValueError(f'Invalid numeric value for {field}: {value}')

    return extracted


def _create_daily_forecasts_from_3h(forecast_list, max_days):
    grouped = {}
    for item in forecast_list:
        dt_txt = item.get('dt_txt')
        if not dt_txt:
            continue

        day = dt_txt.split(' ')[0]
        if day not in grouped:
            if len(grouped) >= max_days:
                break
            grouped[day] = []

        grouped[day].append(item)

    daily_forecasts = []
    for day, entries in grouped.items():
        temp_vals = [e['main']['temp'] for e in entries if 'main' in e]
        humidity_vals = [e['main']['humidity'] for e in entries if 'main' in e]
        pressure_vals = [e['main']['pressure'] for e in entries if 'main' in e]
        wind_vals = [e['wind']['speed'] for e in entries if 'wind' in e]
        clouds_vals = [e['clouds']['all'] for e in entries if 'clouds' in e]

        if not temp_vals:
            continue

        features = {
            'temperature': sum(temp_vals) / len(temp_vals),
            'humidity': sum(humidity_vals) / len(humidity_vals) if humidity_vals else 0,
            'pressure': sum(pressure_vals) / len(pressure_vals) if pressure_vals else 0,
            'wind_speed': sum(wind_vals) / len(wind_vals) if wind_vals else 0,
            'clouds': sum(clouds_vals) / len(clouds_vals) if clouds_vals else 0
        }

        api_prediction = 'Yes' if any(_derive_api_rain_prediction(entry) == 'Yes' for entry in entries) else 'No'
        model_prediction = predict_rainfall(features)

        daily_forecasts.append({
            'date': day,
            'avg_temp': round(features['temperature'], 2),
            'avg_humidity': round(features['humidity'], 2),
            'avg_pressure': round(features['pressure'], 2),
            'avg_wind_speed': round(features['wind_speed'], 2),
            'avg_clouds': round(features['clouds'], 2),
            'api_rain_prediction': api_prediction,
            'model_rain_prediction': model_prediction
        })

    return daily_forecasts


def _create_daily_forecasts_from_daily_api(daily_list, max_days):
    daily_forecasts = []
    for item in daily_list[:max_days]:
        date = ''
        try:
            from datetime import datetime
            date = datetime.utcfromtimestamp(item.get('dt', 0)).strftime('%Y-%m-%d')
        except Exception:
            date = str(item.get('dt', ''))

        temp = item.get('temp', {})
        features = {
            'temperature': float(temp.get('day', 0)),
            'humidity': float(item.get('humidity', 0)),
            'pressure': float(item.get('pressure', 0)),
            'wind_speed': float(item.get('speed', 0)),
            'clouds': float(item.get('clouds', 0))
        }

        api_prediction = _derive_api_rain_prediction(item)
        model_prediction = predict_rainfall(features)

        daily_forecasts.append({
            'date': date,
            'avg_temp': round(features['temperature'], 2),
            'avg_humidity': round(features['humidity'], 2),
            'avg_pressure': round(features['pressure'], 2),
            'avg_wind_speed': round(features['wind_speed'], 2),
            'avg_clouds': round(features['clouds'], 2),
            'api_rain_prediction': api_prediction,
            'model_rain_prediction': model_prediction
        })

    return daily_forecasts


@app.route('/weather', methods=['GET'])
def weather():
    try:
        city = request.args.get('city')
        days = request.args.get('days', default=1, type=int)

        if not city or city.strip() == '':
            return jsonify({'error': 'City parameter is required'}), 400

        logger.info(f"Fetching forecast data for city: {city} (days={days})")

        # Need at least 1 day, and cap at 15 for this feature
        if days < 1:
            days = 1
        requested_days = min(days, 15)

        daily_forecasts = []

        # Try daily 15-day endpoint (if available), fallback to 5-day 3h API
        if requested_days > 1:
            try:
                daily_response = requests.get(
                    f"{OPENWEATHER_FORECAST_URL.replace('/forecast', '/forecast/daily')}?q={city}&cnt={requested_days}&appid={OPENWEATHER_API_KEY}&units=metric"
                )
                if daily_response.status_code == 200:
                    logger.info('Using daily forecast endpoint for multi-day request')
                    daily_forecasts = _create_daily_forecasts_from_daily_api(daily_response.json().get('list', []), requested_days)
                else:
                    logger.warning(f"Daily forecast endpoint failed ({daily_response.status_code}), using 3h endpoint")
            except Exception as e:
                logger.warning(f"Daily endpoint unavailable ({str(e)}), falling back to 3h endpoint")

        forecast_response = requests.get(
            f"{OPENWEATHER_FORECAST_URL}?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
        )

        if forecast_response.status_code == 404:
            return jsonify({'error': 'City not found'}), 404
        if forecast_response.status_code != 200:
            raise Exception(f"OpenWeather API error: {forecast_response.status_code}")

        forecast_data = forecast_response.json()

        # for single-day behavior keep existing logic
        first_forecast = forecast_data['list'][0]
        features = {
            'temperature': first_forecast['main']['temp'],
            'humidity': first_forecast['main']['humidity'],
            'pressure': first_forecast['main']['pressure'],
            'wind_speed': first_forecast['wind']['speed'],
            'clouds': first_forecast['clouds']['all']
        }

        weather_desc = ''
        if 'weather' in first_forecast and first_forecast['weather']:
            weather_desc = first_forecast['weather'][0].get('description', '')

        api_rain_prediction = 'Yes' if ('rain' in weather_desc.lower() or 'thunderstorm' in weather_desc.lower() or first_forecast.get('pop', 0) > 0.4) else 'No'

        model_rain_prediction = predict_rainfall(features)
        rain_prediction = model_rain_prediction if model_rain_prediction is not None else api_rain_prediction

        precipitation_probability = first_forecast.get('pop', 0)
        rain_volume_mm = 0
        if isinstance(first_forecast.get('rain', {}), dict):
            rain_volume_mm = first_forecast['rain'].get('1h', first_forecast['rain'].get('3h', 0))

        response = {
            'city': forecast_data['city']['name'],
            'country': forecast_data['city']['country'],
            'temp': features['temperature'],
            'humidity': features['humidity'],
            'pressure': features['pressure'],
            'wind_speed': features['wind_speed'],
            'clouds': features['clouds'],
            'rain_prediction': rain_prediction,
            'api_rain_prediction': api_rain_prediction,
            'model_rain_prediction': model_rain_prediction,
            'precipitation_probability': precipitation_probability,
            'rain_volume_mm': rain_volume_mm,
            'forecast_time': first_forecast['dt_txt'],
            'prediction_source': 'model' if model_rain_prediction is not None else 'api'
        }

        if requested_days > 1 and not daily_forecasts:
            daily_forecasts = _create_daily_forecasts_from_3h(forecast_data.get('list', []), requested_days)

        if requested_days > 1:
            response['daily_forecasts'] = daily_forecasts
            response['requested_days'] = requested_days

        def save_to_db():
            try:
                save_weather_data(
                    city=response['city'],
                    country=response['country'],
                    temperature=response['temp'],
                    humidity=response['humidity'],
                    pressure=response['pressure'],
                    wind_speed=response['wind_speed'],
                    clouds=response['clouds'],
                    rain_prediction=response['rain_prediction']
                )
                logger.info(f"Weather data saved to database for {response['city']}")
            except Exception as db_error:
                logger.error(f"Error saving to database: {str(db_error)}")

        db_thread = threading.Thread(target=save_to_db, daemon=True)
        db_thread.start()

        logger.info(f"Sending response: {response}")
        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error in /weather endpoint: {str(e)}")
        return jsonify({'error': 'Failed to fetch weather data', 'details': str(e)}), 500

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        if not isinstance(data, dict):
            return jsonify({'error': 'Invalid JSON body, expected an object.'}), 400

        try:
            features = extract_prediction_features(data)
        except KeyError as key_err:
            return jsonify({'error': str(key_err)}), 400
        except ValueError as value_err:
            return jsonify({'error': str(value_err)}), 400

        logger.info(f"Received prediction request with features: {features}")
        prediction = predict_rainfall(features)

        return jsonify({
            'rain_prediction': prediction,
            'raw_features': features,
            'model_loaded': model is not None
        }), 200
    except Exception as e:
        logger.error(f"Error in /predict endpoint: {str(e)}")
        return jsonify({
            'error': f'Internal server error: {str(e)}'
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'Flask backend is running',
        'port': PORT,
        'model_loaded': model is not None
    }), 200

@app.route('/history', methods=['GET'])
def get_weather_history_endpoint():
    try:
        city = request.args.get('city')
        limit = request.args.get('limit', default=50, type=int)
        
        records = get_weather_history(city=city, limit=limit)
        
        result = {
            'count': len(records),
            'data': records
        }
        
        logger.info(f"Retrieved {len(records)} weather records from database")
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error in /history endpoint: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve weather history',
            'details': str(e)
        }), 500

@app.route('/cities', methods=['GET'])
def get_stored_cities_endpoint():
    try:
        cities = get_all_cities()
        
        logger.info(f"Retrieved {len(cities)} unique cities from database")
        return jsonify({
            'count': len(cities),
            'cities': cities
        }), 200
    
    except Exception as e:
        logger.error(f"Error in /cities endpoint: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve cities',
            'details': str(e)
        }), 500

@app.route('/stats/<city>', methods=['GET'])
def get_city_stats_endpoint(city):
    try:
        stats = get_city_stats(city)
        
        if not stats:
            return jsonify({
                'error': f'No data found for city: {city}'
            }), 404
        
        logger.info(f"Retrieved statistics for {city}")
        return jsonify(stats), 200
    
    except Exception as e:
        logger.error(f"Error in /stats endpoint: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve statistics',
            'details': str(e)
        }), 500


@app.route('/clear', methods=['POST'])
def clear_data():
    try:
        success = clear_weather_data()
        if success:
            logger.info('All weather data cleared from database')
            return jsonify({'message': 'All weather data cleared'}), 200
        else:
            raise Exception('Database clear operation failed')
    except Exception as e:
        logger.error(f"Error in /clear endpoint: {str(e)}")
        return jsonify({'error': 'Failed to clear weather data', 'details': str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint not found',
        'available_endpoints': ['/weather', '/predict', '/health', '/history', '/cities', '/stats/<city>']
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        'error': 'Method not allowed'
    }), 405

if __name__ == '__main__':
    logger.info("Starting Flask backend...")
    load_model()
    
    app.run(
        host='localhost',
        port=PORT,
        debug=False,
        use_reloader=False
    )
