const cityInput = document.getElementById('cityInput');
const searchBtn = document.getElementById('searchBtn');
const searchDropdown = document.getElementById('searchDropdown');
const dropdownList = document.getElementById('dropdownList');
const dropdownHeader = document.getElementById('dropdownHeader');
const weatherCard = document.getElementById('weatherCard');
const rainPopup = document.getElementById('rainPopup');
const rainPopupText = document.getElementById('rainPopupText');
const rainfallElement = document.getElementById('rainfall');
let currentRainDetails = null;
const loadingMessage = document.getElementById('loadingMessage');
const errorMessage = document.getElementById('errorMessage');

const FLASK_API_URL = 'http://localhost:5000';

const CITY_SUGGESTIONS = [
    'New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix',
    'Philadelphia', 'San Antonio', 'San Diego', 'Dallas', 'San Jose',
    'Austin', 'Jacksonville', 'Fort Worth', 'Columbus', 'Charlotte',
    'San Francisco', 'Indianapolis', 'Seattle', 'Denver', 'Boston',
    'London', 'Paris', 'Berlin', 'Madrid', 'Rome',
    'Amsterdam', 'Vienna', 'Prague', 'Brussels', 'Athens',
    'Tokyo', 'Beijing', 'Shanghai', 'Hong Kong', 'Singapore',
    'Bangkok', 'Dubai', 'Mumbai', 'Delhi', 'Bangalore',
    'Sydney', 'Melbourne', 'Auckland', 'Cairo', 'Lagos',
    'Mexico City', 'São Paulo', 'Buenos Aires', 'Toronto', 'Vancouver',
    'Moscow', 'Istanbul', 'Bangkok', 'Manila', 'Jakarta',
    'Kathmandu', 'Pokhara', 'Lalitpur', 'Bhaktapur', 'Biratnagar',
    'Janakpur', 'Nepalgunj', 'Dharan', 'Birgunj', 'Gorkha',
    'Ilam', 'Itahari', 'Dhulikhel', 'Narayanghat', 'Hetauda',
    'Butwal', 'Siddharthanagar', 'Jumla', 'Jomsom', 'Tansen',
    'Damak', 'Udaypur', 'Nuwakot', 'Surkhet', 'Tikapur',
    'Kailali', 'Dhangadhi', 'Rajbiraj', 'Khandbari', 'Sankhu',
    'Chainpur', 'Chhatara', 'Lahan', 'Inaruwa', 'Biratnagar',
    'Morang', 'Jhapa', 'Sunsari', 'Saptari', 'Siraha'
];

console.log('Script loaded! Elements:', { cityInput, searchBtn, weatherCard });

function loadSearchHistory() {
    const history = localStorage.getItem('searchHistory');
    return history ? JSON.parse(history) : [];
}

function saveSearchHistory(history) {
    localStorage.setItem('searchHistory', JSON.stringify(history));
}

function deleteCity(city, e) {
    e.stopPropagation();
    let history = loadSearchHistory();
    history = history.filter(c => c.toLowerCase() !== city.toLowerCase());
    saveSearchHistory(history);
    displayDropdown();
}

function displayDropdown() {
    const history = loadSearchHistory();
    const inputValue = cityInput.value.trim();
    
    let itemsToShow = [];

    if (inputValue) {
        const suggestions = CITY_SUGGESTIONS.filter(city =>
            city.toLowerCase().startsWith(inputValue.toLowerCase())
        );
        itemsToShow = suggestions.slice(0, 8);
        
        if (itemsToShow.length === 0) {
            searchDropdown.hidden = true;
            return;
        }
    } else {
        itemsToShow = history;
        if (itemsToShow.length === 0) {
            searchDropdown.hidden = true;
            return;
        }
    }

    dropdownList.innerHTML = '';
    
    if (inputValue) {
        dropdownHeader.hidden = false;
        dropdownHeader.querySelector('.dropdown-title').textContent = `City Suggestions`;
    } else {
        dropdownHeader.hidden = history.length > 0 ? false : true;
        if (dropdownHeader.querySelector('.dropdown-title')) {
            dropdownHeader.querySelector('.dropdown-title').textContent = 'Search History';
        }
    }

    itemsToShow.forEach(city => {
        const li = document.createElement('li');
        
        const cityText = document.createElement('span');
        cityText.className = 'city-text';
        cityText.textContent = city;
        
        li.appendChild(cityText);
        
        if (!inputValue) {
            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'delete-btn';
            deleteBtn.textContent = '✕';
            deleteBtn.title = `Delete ${city}`;
            deleteBtn.addEventListener('click', (e) => deleteCity(city, e));
            li.appendChild(deleteBtn);
        }
        
        li.addEventListener('click', () => {
            cityInput.value = city;
            searchDropdown.hidden = true;
            fetchWeather(city);
        });
        
        dropdownList.appendChild(li);
    });
    
    searchDropdown.hidden = false;
}

cityInput.addEventListener('focus', displayDropdown);

cityInput.addEventListener('input', displayDropdown);

document.addEventListener('click', (e) => {
    const isClickOnSearchArea = cityInput.contains(e.target) || searchDropdown.contains(e.target) || searchBtn.contains(e.target) || weatherCard.contains(e.target);
    const isClickOnRainArea = rainfallElement.contains(e.target) || rainPopup.contains(e.target);
    if (!isClickOnSearchArea) {
        searchDropdown.hidden = true;
    }
    if (!isClickOnRainArea) {
        hideRainPopup();
    }
});

rainfallElement.addEventListener('click', (e) => {
    e.stopPropagation();
    if (!currentRainDetails) return;
    setRainPopupContent(currentRainDetails);
    rainPopup.hidden = false;
    rainPopup.classList.toggle('show');
});

searchBtn.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    const city = cityInput.value.trim();
    if (!city) return;

    let history = loadSearchHistory();
    history = history.filter(c => c.toLowerCase() !== city.toLowerCase());
    history.unshift(city);
    history = history.slice(0, 5);
    saveSearchHistory(history);
    searchDropdown.hidden = true;

    fetchWeather(city);
});

cityInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        e.preventDefault();
        searchBtn.click();
    }
});

async function fetchWeather(city) {
    console.log('fetchWeather called for city:', city);
    loadingMessage.hidden = false;
    errorMessage.hidden = true;
    weatherCard.hidden = true;

    try {
        console.log('Sending request to:', `${FLASK_API_URL}/weather?city=${encodeURIComponent(city)}&days=1`);
        const response = await fetch(`${FLASK_API_URL}/weather?city=${encodeURIComponent(city)}&days=1`);
        console.log('Response received:', response.status, response.statusText);
        console.log('Response object:', response);
        
        if (!response.ok) {
            console.error('Response NOT OK');
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to fetch weather');
        }

        const data = await response.json();
        console.log('Weather data received:', data);
        updateWeatherCard(data);
        console.log('About to set weatherCard.hidden = false');
        weatherCard.hidden = false;
        console.log('Successfully set weatherCard.hidden = false');
        errorMessage.hidden = true;
        console.log('Weather card is now visible');
    } catch (error) {
        console.error('Fetch error:', error);
        errorMessage.textContent = `Error: ${error.message}`;
        errorMessage.hidden = false;
        weatherCard.hidden = true;
    } finally {
        console.log('Finally block - setting loadingMessage.hidden = true');
        loadingMessage.hidden = true;
        console.log('fetchWeather completed');
    }
}

function updateWeatherCard(data) {
    console.log('updateWeatherCard called with data:', data);
    document.getElementById('cityName').textContent = data.city || 'Unknown';
    
    if (data.forecast_time) {
        const nepaliTime = convertToNepaliTime(data.forecast_time);
        document.getElementById('forecastTime').textContent = `Forecast time: ${nepaliTime}`;
    } else {
        document.getElementById('forecastTime').textContent = '';
    }
    
    document.getElementById('temperature').textContent = `${data.temp}°C`;
    document.getElementById('humidity').textContent = `${data.humidity}%`;
    document.getElementById('pressure').textContent = `${data.pressure} hPa`;
    document.getElementById('windSpeed').textContent = `${data.wind_speed} m/s`;
    document.getElementById('cloudCover').textContent = `${data.clouds}%`;
    
    const rainfallElement = document.getElementById('rainfall');
    const rainPrediction = data.rain_prediction && data.rain_prediction.toLowerCase() === 'yes';
    const rainfallValue = rainPrediction ? 'Rain Expected' : 'No Rain';
    
    rainfallElement.textContent = rainfallValue;

    rainfallElement.classList.remove('rain-expected', 'no-rain');
    
    if (rainPrediction) {
        rainfallElement.classList.add('rain-expected');
        changeBackground('rainy');
    } else {
        rainfallElement.classList.add('no-rain');
        changeBackground('sunny');
    }

    currentRainDetails = {
        rainPrediction,
        precipitationProbability: data.precipitation_probability ?? 0,
        rainVolumeMm: data.rain_volume_mm ?? 0,
        source: data.prediction_source || 'api'
    };
    setRainPopupContent(currentRainDetails);
    hideRainPopup();

    // No daily table now: we only show today's prediction.
    console.log('updateWeatherCard completed');
}

function setRainPopupContent(details) {
    if (!details) {
        rainPopupText.textContent = 'No precipitation details available.';
        return;
    }

    const probability = Math.round(details.precipitationProbability * 100);
    const volumeText = details.rainVolumeMm > 0 ? `${details.rainVolumeMm.toFixed(1)} mm expected` : 'No measurable volume available';
    const predictionText = details.rainPrediction ? 'Rain is expected.' : 'Rain is not expected.';

    rainPopupText.textContent = `${predictionText} ${volumeText} | Probability: ${probability}% | Source: ${details.source}.`;
}

function hideRainPopup() {
    rainPopup.classList.remove('show');
    rainPopup.hidden = true;
}

function convertToNepaliTime(utcTimeString) {
    const date = new Date(utcTimeString);
    
    const nepaliOffsetMinutes = 5 * 60 + 45;
    const utcOffsetMinutes = date.getTimezoneOffset();
    const totalOffsetMinutes = nepaliOffsetMinutes + utcOffsetMinutes;
    
    const nepaliDate = new Date(date.getTime() + totalOffsetMinutes * 60000);
    
    const year = nepaliDate.getUTCFullYear();
    const month = String(nepaliDate.getUTCMonth() + 1).padStart(2, '0');
    const day = String(nepaliDate.getUTCDate()).padStart(2, '0');
    const hours = String(nepaliDate.getUTCHours()).padStart(2, '0');
    const minutes = String(nepaliDate.getUTCMinutes()).padStart(2, '0');
    const seconds = String(nepaliDate.getUTCSeconds()).padStart(2, '0');
    
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds} NPT`;
}

function changeBackground(weatherType) {
    document.body.classList.remove('sunny', 'rainy');
    if (weatherType === 'rainy') {
        document.body.classList.add('rainy');
    } else if (weatherType === 'sunny') {
        document.body.classList.add('sunny');
    }
}
