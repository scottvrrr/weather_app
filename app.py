# app.py - Apple Weather style (Imperial units), free APIs
import requests
import os
import logging
from flask import Flask, render_template_string, request, jsonify
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("OWM_API_KEY")
if not API_KEY:
    raise ValueError("OWM_API_KEY not set")

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Weather</title>
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #0a0e14;
            color: #e8edf3;
            font-family: -apple-system, 'Helvetica Neue', sans-serif;
            padding: 16px;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: flex-start;
        }
        .app {
            max-width: 480px;
            width: 100%;
            margin: 0 auto;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0 8px;
            border-bottom: 1px solid rgba(255,255,255,0.08);
            margin-bottom: 20px;
        }
        .header h1 { font-size: 1.5rem; font-weight: 600; letter-spacing: -0.5px; }
        .header-actions button {
            background: rgba(255,255,255,0.08);
            border: none;
            color: #7a8b9f;
            font-size: 1.2rem;
            padding: 6px 12px;
            border-radius: 20px;
            cursor: pointer;
            transition: 0.2s;
            margin-left: 6px;
        }
        .header-actions button:hover { background: rgba(255,255,255,0.15); }
        .search-row {
            display: flex;
            gap: 8px;
            margin-bottom: 20px;
        }
        .search-row input {
            flex: 1;
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 30px;
            padding: 12px 18px;
            color: #e8edf3;
            font-size: 1rem;
            outline: none;
            transition: 0.2s;
        }
        .search-row input::placeholder { color: #6a7b8f; }
        .search-row input:focus { border-color: #4a8eff; background: rgba(255,255,255,0.08); }
        .search-row button {
            background: #4a8eff;
            border: none;
            border-radius: 30px;
            padding: 12px 18px;
            color: white;
            font-weight: 600;
            font-size: 0.9rem;
            cursor: pointer;
            transition: 0.2s;
            white-space: nowrap;
        }
        .search-row button:hover { background: #3a7ae0; transform: scale(1.02); }
        .search-row .loc-btn { background: rgba(255,255,255,0.08); color: #e8edf3; }
        .search-row .loc-btn:hover { background: rgba(255,255,255,0.15); }

        .current-card {
            background: rgba(255,255,255,0.04);
            backdrop-filter: blur(20px);
            border-radius: 32px;
            padding: 24px 22px;
            margin-bottom: 20px;
            border: 1px solid rgba(255,255,255,0.06);
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
        }
        .temp-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .temp-main {
            font-size: 4.2rem;
            font-weight: 300;
            letter-spacing: -2px;
            line-height: 1;
        }
        .temp-main small { font-size: 1.8rem; font-weight: 300; color: #8a9bb0; }
        .condition-text {
            font-size: 1.2rem;
            font-weight: 500;
            margin: 4px 0 2px;
        }
        .high-low {
            font-size: 1rem;
            color: #8a9bb0;
        }
        .extra-details {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 12px;
            margin-top: 18px;
            padding-top: 16px;
            border-top: 1px solid rgba(255,255,255,0.06);
        }
        .extra-detail {
            text-align: center;
        }
        .extra-detail .label { font-size: 0.7rem; text-transform: uppercase; color: #6a7b8f; letter-spacing: 0.5px; }
        .extra-detail .value { font-size: 1.1rem; font-weight: 500; margin-top: 2px; }

        .section-title {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin: 20px 0 10px;
            padding: 0 4px;
        }
        .section-title h3 { font-size: 1rem; font-weight: 600; color: #aabbcc; letter-spacing: 0.3px; }
        .section-title span { font-size: 0.75rem; color: #6a7b8f; }
        .hourly-scroll {
            display: flex;
            overflow-x: auto;
            gap: 14px;
            padding: 8px 4px 16px;
            scroll-snap-type: x mandatory;
            -webkit-overflow-scrolling: touch;
        }
        .hourly-scroll::-webkit-scrollbar { height: 4px; background: transparent; }
        .hourly-scroll::-webkit-scrollbar-thumb { background: #4a5a6a; border-radius: 4px; }
        .hour-item {
            flex: 0 0 70px;
            text-align: center;
            background: rgba(255,255,255,0.03);
            border-radius: 20px;
            padding: 10px 6px;
            border: 1px solid rgba(255,255,255,0.04);
            scroll-snap-align: start;
            transition: 0.2s;
        }
        .hour-item:hover { background: rgba(255,255,255,0.06); }
        .hour-item .time { font-size: 0.8rem; color: #8a9bb0; }
        .hour-item .temp { font-size: 1.2rem; font-weight: 500; margin: 4px 0; }
        .hour-item .icon { font-size: 1.3rem; }
        .hour-item .pop { font-size: 0.7rem; color: #6a9bff; }

        .daily-list {
            display: flex;
            flex-direction: column;
            gap: 6px;
            margin-top: 8px;
        }
        .day-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(255,255,255,0.02);
            padding: 12px 16px;
            border-radius: 16px;
            border: 1px solid rgba(255,255,255,0.04);
            transition: 0.15s;
        }
        .day-item:hover { background: rgba(255,255,255,0.05); }
        .day-item .day-name { font-weight: 500; width: 70px; }
        .day-item .day-icon { font-size: 1.2rem; width: 40px; text-align: center; }
        .day-item .day-temps .high { color: #e8edf3; }
        .day-item .day-temps .low { color: #8a9bb0; margin-left: 8px; }
        .day-item .day-pop { font-size: 0.8rem; color: #6a9bff; width: 50px; text-align: right; }

        .loading-state { text-align: center; padding: 40px 0; color: #6a7b8f; }
        .error-state { background: rgba(255,70,70,0.08); border: 1px solid rgba(255,70,70,0.2); border-radius: 16px; padding: 20px; color: #ff7a7a; text-align: center; }
        .debug-box {
            background: rgba(0,0,0,0.4);
            border-radius: 12px;
            padding: 8px 12px;
            font-size: 0.7rem;
            color: #4a6a5a;
            margin-top: 20px;
            max-height: 80px;
            overflow-y: auto;
            display: none;
            font-family: monospace;
            border: 1px solid rgba(255,255,255,0.04);
        }
        .debug-box::-webkit-scrollbar { width: 4px; background: transparent; }
        .debug-box::-webkit-scrollbar-thumb { background: #3a4a4a; border-radius: 4px; }
    </style>
</head>
<body>
<div class="app">
    <div class="header">
        <h1>⛅ Weather</h1>
        <div class="header-actions">
            <button onclick="fetchByLocation()" title="My Location">📍</button>
            <button onclick="document.getElementById('zipInput').value=''; fetchByZip();" title="Refresh">⟳</button>
        </div>
    </div>

    <div class="search-row">
        <input id="zipInput" placeholder="ZIP code (e.g., 43065)" value="">
        <button onclick="fetchByZip()">Search</button>
        <button class="loc-btn" onclick="fetchByLocation()">📍</button>
    </div>

    <div id="content">
        <div class="loading-state">Enter a ZIP or tap location</div>
    </div>

    <div id="debug" class="debug-box"></div>
</div>

<script>
(function() {
    const debugEl = document.getElementById('debug');
    function logDebug(msg) {
        debugEl.style.display = 'block';
        const line = document.createElement('div');
        line.textContent = new Date().toLocaleTimeString() + ' :: ' + msg;
        debugEl.appendChild(line);
        debugEl.scrollTop = debugEl.scrollHeight;
    }

    function showLoading(text) {
        document.getElementById('content').innerHTML = `<div class="loading-state">⏳ ${text}</div>`;
    }

    function showError(msg) {
        document.getElementById('content').innerHTML = `<div class="error-state">⚠️ ${msg}</div>`;
        logDebug('ERROR: ' + msg);
    }

    function getWeatherIcon(desc) {
        const d = desc.toLowerCase();
        if (d.includes('clear')) return '☀️';
        if (d.includes('cloud')) return '☁️';
        if (d.includes('rain')) return '🌧️';
        if (d.includes('thunder')) return '⛈️';
        if (d.includes('snow')) return '❄️';
        if (d.includes('mist') || d.includes('fog')) return '🌫️';
        return '🌤️';
    }

    function formatDay(isoDate) {
        const days = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
        const d = new Date(isoDate + 'T00:00:00Z');
        return days[d.getUTCDay()];
    }

    function renderWeather(data) {
        const c = data.current;
        const hourly = data.hourly;
        const daily = data.daily;

        let html = '';
        // Current card
        html += `<div class="current-card">
            <div class="temp-row">
                <div>
                    <div class="temp-main">${Math.round(c.temp)}°<small>F</small></div>
                    <div class="condition-text">${c.description}</div>
                    <div class="high-low">H: ${Math.round(c.temp_max)}° · L: ${Math.round(c.temp_min)}°</div>
                </div>
                <div style="font-size:4rem;">${getWeatherIcon(c.description)}</div>
            </div>
            <div class="extra-details">
                <div class="extra-detail"><div class="label">Feels Like</div><div class="value">${Math.round(c.feels_like)}°</div></div>
                <div class="extra-detail"><div class="label">Humidity</div><div class="value">${c.humidity}%</div></div>
                <div class="extra-detail"><div class="label">Wind</div><div class="value">${Math.round(c.wind_speed)} mph</div></div>
                <div class="extra-detail"><div class="label">Pressure</div><div class="value">${c.pressure} hPa</div></div>
                <div class="extra-detail"><div class="label">UV Index</div><div class="value">${c.uvi !== undefined ? c.uvi : '—'}</div></div>
                <div class="extra-detail"><div class="label">Visibility</div><div class="value">${(c.visibility / 1609).toFixed(1)} mi</div></div>
            </div>
            <div style="margin-top:12px; font-size:0.8rem; color:#6a7b8f; display:flex; justify-content:space-between;">
                <span>☀️ Rise ${c.sunrise.slice(11,16)}</span>
                <span>🌇 Set ${c.sunset.slice(11,16)}</span>
            </div>
        </div>`;

        // Hourly scroll
        html += `<div class="section-title"><h3>Hourly</h3><span>next 24h</span></div>
        <div class="hourly-scroll">`;
        hourly.slice(0,8).forEach(h => {
            html += `<div class="hour-item">
                <div class="time">${h.time.slice(11,16)}</div>
                <div class="icon">${getWeatherIcon(h.description)}</div>
                <div class="temp">${Math.round(h.temp)}°</div>
                <div class="pop">${h.pop > 0 ? Math.round(h.pop*100)+'%' : ''}</div>
            </div>`;
        });
        html += `</div>`;

        // Daily list
        html += `<div class="section-title"><h3>5-Day Forecast</h3></div><div class="daily-list">`;
        daily.forEach(d => {
            const dayName = d.date === new Date().toISOString().slice(0,10) ? 'Today' : formatDay(d.date);
            html += `<div class="day-item">
                <span class="day-name">${dayName}</span>
                <span class="day-icon">${getWeatherIcon(d.description)}</span>
                <span class="day-temps"><span class="high">${Math.round(d.temp_max)}°</span><span class="low">${Math.round(d.temp_min)}°</span></span>
                <span class="day-pop">${d.pop > 0 ? Math.round(d.pop*100)+'%' : ''}</span>
            </div>`;
        });
        html += `</div>`;

        document.getElementById('content').innerHTML = html;
        logDebug('Display updated');
    }

    function fetchWeather(lat, lon) {
        logDebug('Fetching lat='+lat.toFixed(4)+' lon='+lon.toFixed(4));
        showLoading('Fetching weather...');
        fetch(`/api/weather?lat=${lat}&lon=${lon}`)
            .then(r => r.json())
            .then(data => {
                if (data.error) throw new Error(data.error);
                renderWeather(data);
            })
            .catch(err => {
                logDebug('Error: '+err.message);
                showError(err.message);
            });
    }

    window.fetchByZip = function() {
        const zip = document.getElementById('zipInput').value.trim();
        if (!zip) { alert('Enter a ZIP code'); return; }
        logDebug('ZIP: '+zip);
        showLoading('Looking up ZIP...');
        fetch(`/api/zip?zip=${zip}`)
            .then(r => r.json())
            .then(data => {
                if (data.error) throw new Error(data.error);
                fetchWeather(data.lat, data.lon);
            })
            .catch(err => {
                logDebug('ZIP error: '+err.message);
                showError('ZIP: '+err.message);
            });
    };

    window.fetchByLocation = function() {
        if (!navigator.geolocation) {
            alert('Geolocation not supported');
            return;
        }
        showLoading('Getting location...');
        navigator.geolocation.getCurrentPosition(
            pos => fetchWeather(pos.coords.latitude, pos.coords.longitude),
            err => {
                logDebug('Geolocation error: '+err.message);
                showError('Location: '+err.message);
            }
        );
    };

    logDebug('App ready');
})();
</script>
</body>
</html>
"""

def geocode_zip(zip_code):
    url = f"http://api.openweathermap.org/geo/1.0/zip?zip={zip_code},US&appid={API_KEY}"
    resp = requests.get(url, timeout=10)
    if resp.status_code != 200:
        url2 = f"http://api.openweathermap.org/geo/1.0/zip?zip={zip_code}&appid={API_KEY}"
        resp2 = requests.get(url2, timeout=10)
        if resp2.status_code != 200:
            raise ValueError(f"ZIP not found (HTTP {resp2.status_code}): {zip_code}")
        data = resp2.json()
    else:
        data = resp.json()
    if "lat" not in data:
        raise ValueError(f"ZIP not found: {zip_code}")
    return data["lat"], data["lon"]

def get_weather_data(lat, lon):
    # Current weather (imperial units)
    url_curr = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=imperial"
    curr_resp = requests.get(url_curr, timeout=10)
    curr = curr_resp.json()
    if curr_resp.status_code != 200:
        raise ValueError(f"Weather API error: {curr.get('message', 'Unknown')}")
    
    # 5-day forecast (imperial)
    url_fore = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=imperial"
    fore_resp = requests.get(url_fore, timeout=10)
    fore = fore_resp.json()
    if fore_resp.status_code != 200:
        raise ValueError(f"Forecast API error: {fore.get('message', 'Unknown')}")

    # Current
    current = {
        "temp": curr["main"]["temp"],
        "feels_like": curr["main"]["feels_like"],
        "temp_min": curr["main"]["temp_min"],
        "temp_max": curr["main"]["temp_max"],
        "humidity": curr["main"]["humidity"],
        "pressure": curr["main"]["pressure"],
        "wind_speed": curr["wind"]["speed"],
        "clouds": curr["clouds"]["all"],
        "visibility": curr.get("visibility", 10000),
        "description": curr["weather"][0]["description"],
        "sunrise": datetime.fromtimestamp(curr["sys"]["sunrise"], tz=timezone.utc).isoformat(),
        "sunset": datetime.fromtimestamp(curr["sys"]["sunset"], tz=timezone.utc).isoformat(),
        "uvi": None  # not available in free current
    }
    
    # Hourly (8 items = 24h)
    hourly = []
    for item in fore["list"][:8]:
        hourly.append({
            "time": datetime.fromtimestamp(item["dt"], tz=timezone.utc).isoformat(),
            "temp": item["main"]["temp"],
            "description": item["weather"][0]["description"],
            "pop": item.get("pop", 0.0),
            "wind_speed": item["wind"]["speed"]
        })
    
    # Daily (group by date, max 5)
    daily = []
    dates_seen = set()
    for item in fore["list"]:
        date_str = datetime.fromtimestamp(item["dt"], tz=timezone.utc).isoformat()[:10]
        if date_str not in dates_seen and len(daily) < 5:
            dates_seen.add(date_str)
            daily.append({
                "date": date_str,
                "temp_max": item["main"]["temp_max"],
                "temp_min": item["main"]["temp_min"],
                "description": item["weather"][0]["description"],
                "pop": item.get("pop", 0.0)
            })
    
    return {"current": current, "hourly": hourly, "daily": daily}

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/weather')
def api_weather():
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    if not lat or not lon:
        return jsonify({"error": "Missing lat/lon"}), 400
    try:
        data = get_weather_data(float(lat), float(lon))
        return jsonify(data)
    except Exception as e:
        app.logger.error(f"Weather error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/zip')
def api_zip():
    zip_code = request.args.get('zip')
    if not zip_code:
        return jsonify({"error": "Missing zip"}), 400
    try:
        lat, lon = geocode_zip(zip_code)
        return jsonify({"lat": lat, "lon": lon})
    except Exception as e:
        app.logger.error(f"ZIP error: {str(e)}")
        return jsonify({"error": str(e)}), 404

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
