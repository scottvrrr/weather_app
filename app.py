# app.py - Flask web server for Railway deployment
# Requirements: flask, requests, python-dotenv, gunicorn (in requirements.txt)

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

# HTML template with embedded CSS (dark theme, responsive)
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
        .search { display: flex; gap: 10px; margin-bottom: 20px; }
        .loading { opacity: 0.6; }
    </style>
</head>
<body>
    <h1>⛅ Hyperlocal Weather</h1>
    <div class="search">
        <input id="lat" placeholder="Latitude" value="40.7128">
        <input id="lon" placeholder="Longitude" value="-74.0060">
        <button onclick="fetchWeather()">Update</button>
    </div>
    <div id="content">
        <div class="card loading">Loading...</div>
    </div>
    <script>
        function fetchWeather() {
            const lat = document.getElementById('lat').value;
            const lon = document.getElementById('lon').value;
            document.getElementById('content').innerHTML = '<div class="card loading">Updating...</div>';
            fetch(`/api/weather?lat=${lat}&lon=${lon}`)
                .then(r => r.json())
                .then(data => {
                    let html = '';
                    // Current
                    const c = data.current;
                    html += `<div class="card"><div class="flex"><div><span class="temp-big">${c.temp}°C</span> <span class="metric">feels ${c.feels_like}°C</span><br>
                        ${c.description} · Humidity ${c.humidity}% · Pressure ${c.pressure} hPa</div>
                        <div>Wind ${c.wind_speed} m/s · Clouds ${c.clouds}% · Visibility ${c.visibility/1000} km</div></div>
                        <div>Sunrise ${c.sunrise.slice(11,16)} UTC · Sunset ${c.sunset.slice(11,16)} UTC</div></div>`;
                    // Hourly (12)
                    html += `<div class="card"><h3>Next 12 hours</h3><div class="hourly-grid">`;
                    data.hourly.slice(0,12).forEach(h => {
                        html += `<div class="hour-item">${h.time.slice(11,16)}<br><strong>${h.temp}°</strong><br>${h.description}<br><span class="rain">☔ ${(h.pop*100).toFixed(0)}%</span> · <span class="wind">💨 ${h.wind_speed}</span></div>`;
                    });
                    html += `</div></div>`;
                    // Daily (7)
                    html += `<div class="card"><h3>7-Day Forecast</h3><div class="daily-grid">`;
                    data.daily.forEach(d => {
                        html += `<div class="day-item">${d.date.slice(5)}<br><strong>${d.temp_day}°</strong> / ${d.temp_night}°<br>${d.description}<br><span class="rain">☔ ${(d.pop*100).toFixed(0)}%</span></div>`;
                    });
                    html += `</div></div>`;
                    document.getElementById('content').innerHTML = html;
                })
                .catch(err => document.getElementById('content').innerHTML = `<div class="card">Error: ${err.message}</div>`);
        }
        fetchWeather();
    </script>
</body>
</html>
"""

def get_weather_data(lat, lon):
    # Current
    url_curr = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    curr = requests.get(url_curr, timeout=10).json()
    # OneCall for hourly/daily
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
    lat = request.args.get('lat', '40.7128')
    lon = request.args.get('lon', '-74.0060')
    try:
        data = get_weather_data(lat, lon)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
