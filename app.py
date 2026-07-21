# app.py - Flask with zip code + browser geolocation
import requests
import os
from flask import Flask, render_template_string, request, jsonify
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("OWM_API_KEY")
if not API_KEY:
    raise ValueError("OWM_API_KEY not set")

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Weather App</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #0b0e14; color: #e0e4ec; padding: 20px; max-width: 900px; margin: auto; }
        .card { background: #1a1f2a; border-radius: 16px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }
        .flex { display: flex; flex-wrap: wrap; gap: 20px; justify-content: space-between; }
        .temp-big { font-size: 3rem; font-weight: 300; }
        .metric { color: #8b9bb5; }
        .hourly-grid, .daily-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px,1fr)); gap: 12px; }
        .hour-item, .day-item { background: #252c3b; border-radius: 12px; padding: 10px; text-align: center; }
        .rain { color: #5fc3e4; }
        .wind { color: #a0b8cc; }
        input, button { padding: 10px 16px; border: none; border-radius: 8px; background: #252c3b; color: #e0e4ec; }
        button { background: #3b4a5e; cursor: pointer; }
        button:hover { background: #4f617a; }
        .search { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        .search input { flex: 1; min-width: 120px; }
        .location-btn { background: #2a4a5e; }
        .location-btn:hover { background: #3a6a7e; }
        .loading { opacity: 0.6; }
    </style>
</head>
<body>
    <h1>⛅ Hyperlocal Weather</h1>
    <div class="search">
        <input id="zipInput" placeholder="Enter ZIP code (e.g., 10001)" value="">
        <button onclick="fetchByZip()">Get ZIP</button>
        <button class="location-btn" onclick="fetchByLocation()">📍 My Location</button>
    </div>
    <div id="content">
        <div class="card loading">Enter a ZIP or tap "My Location"</div>
    </div>
    <script>
        function fetchWeather(lat, lon) {
            document.getElementById('content').innerHTML = '<div class="card loading">Updating...</div>';
            fetch(`/api/weather?lat=${lat}&lon=${lon}`)
                .then(r => r.json())
                .then(data => {
                    if (data.error) { throw new Error(data.error); }
                    let html = '';
                    const c = data.current;
                    html += `<div class="card"><div class="flex"><div><span class="temp-big">${c.temp}°C</span> <span class="metric">feels ${c.feels_like}°C</span><br>
                        ${c.description} · Humidity ${c.humidity}% · Pressure ${c.pressure} hPa</div>
                        <div>Wind ${c.wind_speed} m/s · Clouds ${c.clouds}% · Visibility ${c.visibility/1000} km</div></div>
                        <div>Sunrise ${c.sunrise.slice(11,16)} UTC · Sunset ${c.sunset.slice(11,16)} UTC</div></div>`;
                    html += `<div class="card"><h3>Next 12 hours</h3><div class="hourly-grid">`;
                    data.hourly.slice(0,12).forEach(h => {
                        html += `<div class="hour-item">${h.time.slice(11,16)}<br><strong>${h.temp}°</strong><br>${h.description}<br><span class="rain">☔ ${(h.pop*100).toFixed(0)}%</span> · <span class="wind">💨 ${h.wind_speed}</span></div>`;
                    });
                    html += `</div></div>`;
                    html += `<div class="card"><h3>7-Day Forecast</h3><div class="daily-grid">`;
                    data.daily.forEach(d => {
                        html += `<div class="day-item">${d.date.slice(5)}<br><strong>${d.temp_day}°</strong> / ${d.temp_night}°<br>${d.description}<br><span class="rain">☔ ${(d.pop*100).toFixed(0)}%</span></div>`;
                    });
                    html += `</div></div>`;
                    document.getElementById('content').innerHTML = html;
                })
                .catch(err => document.getElementById('content').innerHTML = `<div class="card">Error: ${err.message}</div>`);
        }

        function fetchByZip() {
            const zip = document.getElementById('zipInput').value.trim();
            if (!zip) { alert('Enter a ZIP code'); return; }
            fetch(`/api/zip?zip=${zip}`)
                .then(r => r.json())
                .then(data => {
                    if (data.error) { throw new Error(data.error); }
                    fetchWeather(data.lat, data.lon);
                })
                .catch(err => document.getElementById('content').innerHTML = `<div class="card">ZIP error: ${err.message}</div>`);
        }

        function fetchByLocation() {
            if (!navigator.geolocation) {
                alert('Geolocation not supported by your browser');
                return;
            }
            navigator.geolocation.getCurrentPosition(
                pos => fetchWeather(pos.coords.latitude, pos.coords.longitude),
                err => document.getElementById('content').innerHTML = `<div class="card">Location denied or error: ${err.message}</div>`
            );
        }

        // Auto-load with default NYC if no action
        window.onload = function() {
            // Optionally try location on load, but we leave it manual.
        };
    </script>
</body>
</html>
"""

def geocode_zip(zip_code):
    # OpenWeather geocoding API – zip to lat/lon
    url = f"http://api.openweathermap.org/geo/1.0/zip?zip={zip_code}&appid={API_KEY}"
    resp = requests.get(url, timeout=10).json()
    if "lat" not in resp:
        raise ValueError(f"ZIP not found: {zip_code}")
    return resp["lat"], resp["lon"]

def get_weather_data(lat, lon):
    url_curr = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    curr = requests.get(url_curr, timeout=10).json()
    url_one = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&exclude=minutely,alerts&appid={API_KEY}&units=metric"
    one = requests.get(url_one, timeout=10).json()
    
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
        return jsonify({"error": str(e)}), 404

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
