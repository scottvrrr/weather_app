# app.py - Clean modern weather (ZIP + geolocation) with debug output
import requests
import os
import logging
from flask import Flask, render_template_string, request, jsonify
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("OWM_API_KEY")
if not API_KEY:
    raise ValueError("OWM_API_KEY not set - add to Railway variables")

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Weather App</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f0f4f8;
            color: #1a202c;
            padding: 20px;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .container {
            max-width: 800px;
            width: 100%;
            background: white;
            border-radius: 24px;
            padding: 30px 24px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.08);
        }
        h1 { font-size: 1.8rem; font-weight: 600; margin-bottom: 20px; color: #2d3748; }
        .row {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 24px;
        }
        .row input {
            flex: 2;
            min-width: 160px;
            padding: 12px 16px;
            border: 2px solid #e2e8f0;
            border-radius: 12px;
            font-size: 1rem;
            outline: none;
            transition: 0.2s;
        }
        .row input:focus { border-color: #3182ce; }
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 12px;
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            transition: 0.2s;
            background: #3182ce;
            color: white;
            flex: 1;
            min-width: 100px;
        }
        .btn:hover { background: #2b6cb0; transform: scale(1.01); }
        .btn-loc { background: #38a169; }
        .btn-loc:hover { background: #2f855a; }
        .card {
            background: #f7fafc;
            border-radius: 16px;
            padding: 18px 20px;
            margin-top: 16px;
            border: 1px solid #e2e8f0;
        }
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 24px; }
        .grid-3 { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px,1fr)); gap: 12px; margin-top: 12px; }
        .hour-item, .day-item {
            background: white;
            border-radius: 12px;
            padding: 10px 8px;
            text-align: center;
            border: 1px solid #e2e8f0;
            font-size: 0.9rem;
        }
        .temp-big { font-size: 3rem; font-weight: 300; }
        .dim { color: #718096; }
        .rain { color: #2b6cb0; }
        .wind { color: #38a169; }
        .loading { text-align: center; padding: 30px; color: #718096; }
        .error { color: #e53e3e; border-color: #fed7d7; background: #fff5f5; }
        .debug-box { background: #edf2f7; padding: 10px; border-radius: 8px; font-size: 0.75rem; margin-top: 12px; color: #4a5568; overflow-wrap: break-word; }
        @media (max-width: 480px) {
            .row input { min-width: 100px; }
            .btn { min-width: 70px; font-size: 0.85rem; padding: 10px 12px; }
            .temp-big { font-size: 2.2rem; }
            .grid-2 { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
<div class="container">
    <h1>⛅ Weather</h1>
    <div class="row">
        <input id="zipInput" placeholder="ZIP code (e.g., 43065)" value="">
        <button class="btn" onclick="fetchByZip()">Search ZIP</button>
        <button class="btn btn-loc" onclick="fetchByLocation()">📍 My Location</button>
    </div>
    <div id="content">
        <div class="card loading">Enter a ZIP or use your location</div>
    </div>
    <div id="debug" class="debug-box" style="display:none;"></div>
</div>

<script>
function logDebug(msg) {
    const el = document.getElementById('debug');
    el.style.display = 'block';
    el.innerHTML += new Date().toLocaleTimeString() + ' :: ' + msg + '<br>';
}

function fetchWeather(lat, lon) {
    logDebug('Fetching weather for lat='+lat+' lon='+lon);
    document.getElementById('content').innerHTML = '<div class="card loading">Loading...</div>';
    fetch(`/api/weather?lat=${lat}&lon=${lon}`)
        .then(r => r.json())
        .then(data => {
            logDebug('Response received');
            if (data.error) throw new Error(data.error);
            let html = '';
            const c = data.current;
            html += `<div class="card">
                <div style="display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;">
                    <div><span class="temp-big">${Math.round(c.temp)}°C</span> <span class="dim">feels ${Math.round(c.feels_like)}°C</span></div>
                    <div style="text-align:right;font-size:1.1rem;">${c.description.toUpperCase()}<br><span class="dim">Humidity ${c.humidity}% · Pressure ${c.pressure} hPa</span></div>
                </div>
                <div class="grid-2" style="margin-top:12px;">
                    <div>💨 Wind ${c.wind_speed} m/s</div>
                    <div>☁️ Clouds ${c.clouds}%</div>
                    <div>👁 Visibility ${(c.visibility/1000).toFixed(1)} km</div>
                    <div>🌅 ${c.sunrise.slice(11,16)} UTC · 🌇 ${c.sunset.slice(11,16)} UTC</div>
                </div>
            </div>`;
            html += `<div class="card"><div style="font-weight:600;margin-bottom:8px;">Next 12 hours</div><div class="grid-3">`;
            data.hourly.slice(0,12).forEach(h => {
                html += `<div class="hour-item">${h.time.slice(11,16)}<br><strong>${Math.round(h.temp)}°</strong><br><span class="dim">${h.description.slice(0,14)}</span><br><span class="rain">☔ ${(h.pop*100).toFixed(0)}%</span> <span class="wind">💨${Math.round(h.wind_speed)}</span></div>`;
            });
            html += `</div></div>`;
            html += `<div class="card"><div style="font-weight:600;margin-bottom:8px;">7-Day Forecast</div><div class="grid-3">`;
            data.daily.forEach(d => {
                html += `<div class="day-item">${d.date.slice(5)}<br><strong>${Math.round(d.temp_day)}°</strong> <span class="dim">/${Math.round(d.temp_night)}°</span><br><span class="dim">${d.description.slice(0,14)}</span><br><span class="rain">☔ ${(d.pop*100).toFixed(0)}%</span></div>`;
            });
            html += `</div></div>`;
            document.getElementById('content').innerHTML = html;
            logDebug('Display updated');
        })
        .catch(err => {
            logDebug('ERROR: '+err.message);
            document.getElementById('content').innerHTML = `<div class="card error">⚠️ ${err.message}</div>`;
        });
}

function fetchByZip() {
    const zip = document.getElementById('zipInput').value.trim();
    if (!zip) { alert('Enter a ZIP code'); return; }
    logDebug('Fetching ZIP: '+zip);
    document.getElementById('content').innerHTML = '<div class="card loading">Looking up ZIP...</div>';
    fetch(`/api/zip?zip=${zip}`)
        .then(r => r.json())
        .then(data => {
            logDebug('ZIP response: '+JSON.stringify(data));
            if (data.error) throw new Error(data.error);
            fetchWeather(data.lat, data.lon);
        })
        .catch(err => {
            logDebug('ZIP ERROR: '+err.message);
            document.getElementById('content').innerHTML = `<div class="card error">⚠️ ZIP error: ${err.message}</div>`;
        });
}

function fetchByLocation() {
    logDebug('Requesting geolocation');
    if (!navigator.geolocation) {
        alert('Geolocation not supported');
        return;
    }
    navigator.geolocation.getCurrentPosition(
        pos => {
            logDebug('Location obtained: '+pos.coords.latitude+','+pos.coords.longitude);
            fetchWeather(pos.coords.latitude, pos.coords.longitude);
        },
        err => {
            logDebug('Geolocation error: '+err.message);
            document.getElementById('content').innerHTML = `<div class="card error">⚠️ Location denied: ${err.message}</div>`;
        }
    );
}
</script>
</body>
</html>
"""

def geocode_zip(zip_code):
    # Try US first
    url = f"http://api.openweathermap.org/geo/1.0/zip?zip={zip_code},US&appid={API_KEY}"
    resp = requests.get(url, timeout=10)
    log_debug(f"ZIP geocode URL: {url}")
    log_debug(f"ZIP geocode status: {resp.status_code}")
    if resp.status_code != 200:
        # Try without country
        url2 = f"http://api.openweathermap.org/geo/1.0/zip?zip={zip_code}&appid={API_KEY}"
        resp2 = requests.get(url2, timeout=10)
        log_debug(f"Fallback URL: {url2} status: {resp2.status_code}")
        if resp2.status_code != 200:
            raise ValueError(f"ZIP not found (HTTP {resp2.status_code}): {zip_code}")
        data = resp2.json()
    else:
        data = resp.json()
    if "lat" not in data:
        raise ValueError(f"ZIP not found: {zip_code}")
    return data["lat"], data["lon"]

def log_debug(msg):
    app.logger.debug(msg)

def get_weather_data(lat, lon):
    log_debug(f"get_weather_data called with lat={lat} lon={lon}")
    url_curr = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    curr_resp = requests.get(url_curr, timeout=10)
    log_debug(f"Current weather status: {curr_resp.status_code}")
    curr = curr_resp.json()
    if curr_resp.status_code != 200:
        raise ValueError(f"Weather API error: {curr.get('message', 'Unknown')}")
    
    url_one = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&exclude=minutely,alerts&appid={API_KEY}&units=metric"
    one_resp = requests.get(url_one, timeout=10)
    log_debug(f"OneCall status: {one_resp.status_code}")
    one = one_resp.json()
    if one_resp.status_code != 200:
        raise ValueError(f"OneCall API error: {one.get('message', 'Unknown')}")

    current = {
        "temp": curr["main"]["temp"],
        "feels_like": curr["main"]["feels_like"],
        "humidity": curr["main"]["humidity"],
        "pressure": curr["main"]["pressure"],
        "wind_speed": curr["wind"]["speed"],
        "clouds": curr["clouds"]["all"],
        "visibility": curr.get("visibility", 10000),
        "description": curr["weather"][0]["description"],
        "sunrise": datetime.fromtimestamp(curr["sys"]["sunrise"], tz=timezone.utc).isoformat(),
        "sunset": datetime.fromtimestamp(curr["sys"]["sunset"], tz=timezone.utc).isoformat()
    }
    hourly = []
    for h in one["hourly"][:48]:
        hourly.append({
            "time": datetime.fromtimestamp(h["dt"], tz=timezone.utc).isoformat(),
            "temp": h["temp"],
            "description": h["weather"][0]["description"],
            "pop": h.get("pop", 0.0),
            "wind_speed": h["wind_speed"]
        })
    daily = []
    for d in one["daily"][:7]:
        daily.append({
            "date": datetime.fromtimestamp(d["dt"], tz=timezone.utc).isoformat()[:10],
            "temp_day": d["temp"]["day"],
            "temp_night": d["temp"]["night"],
            "description": d["weather"][0]["description"],
            "pop": d.get("pop", 0.0)
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
    app.run(host='0.0.0.0', port=port, debug=True)
