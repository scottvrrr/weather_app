# app.py - Retro terminal weather (ZIP + geolocation)
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
    <title>WEATHER :: TERMINAL v1.0</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #0a0f0a;
            color: #33ff33;
            font-family: 'Courier New', Courier, monospace;
            padding: 20px;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .terminal {
            max-width: 780px;
            width: 100%;
            background: #0f140f;
            border: 2px solid #33ff33;
            border-radius: 12px;
            padding: 24px 20px;
            box-shadow: 0 0 30px rgba(51, 255, 51, 0.15);
        }
        .header {
            font-size: 1.5rem;
            font-weight: bold;
            letter-spacing: 2px;
            border-bottom: 1px dashed #33ff33;
            padding-bottom: 10px;
            margin-bottom: 18px;
            text-align: center;
        }
        .header span { opacity: 0.7; }
        .row {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 18px;
        }
        .row input {
            flex: 2;
            min-width: 150px;
            background: #0f140f;
            border: 1px solid #33ff33;
            color: #33ff33;
            font-family: 'Courier New', Courier, monospace;
            font-size: 1rem;
            padding: 10px 12px;
            border-radius: 6px;
            outline: none;
        }
        .row input::placeholder { color: #1f4f1f; }
        .row input:focus { border-color: #66ff66; background: #0f1a0f; }
        .btn {
            background: #0f140f;
            border: 1px solid #33ff33;
            color: #33ff33;
            font-family: 'Courier New', Courier, monospace;
            font-size: 1rem;
            padding: 10px 18px;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.15s;
            flex: 1;
            min-width: 100px;
            text-align: center;
        }
        .btn:hover { background: #1f3f1f; box-shadow: 0 0 12px #33ff3344; }
        .btn-loc { border-color: #33ccff; color: #33ccff; }
        .btn-loc:hover { background: #1f2f3f; box-shadow: 0 0 12px #33ccff44; }
        .card {
            border: 1px solid #33ff33;
            border-radius: 8px;
            padding: 16px 14px;
            margin-top: 14px;
            background: #0c120c;
        }
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 20px; }
        .grid-3 { display: grid; grid-template-columns: repeat(auto-fill, minmax(110px,1fr)); gap: 10px; margin-top: 10px; }
        .hour-item, .day-item {
            border: 1px solid #1f4f1f;
            border-radius: 6px;
            padding: 8px 6px;
            text-align: center;
            background: #0a120a;
            font-size: 0.85rem;
        }
        .temp-big { font-size: 2.8rem; font-weight: bold; letter-spacing: 1px; }
        .dim { opacity: 0.6; }
        .rain { color: #66ddff; }
        .wind { color: #88dd88; }
        .loading { opacity: 0.5; text-align: center; padding: 20px; }
        .error { color: #ff6666; border-color: #ff6666; }
        .footer { margin-top: 16px; font-size: 0.75rem; opacity: 0.4; text-align: center; border-top: 1px dashed #1f3f1f; padding-top: 12px; }
        @media (max-width: 480px) {
            .row input { min-width: 100px; }
            .btn { min-width: 70px; font-size: 0.85rem; padding: 8px 10px; }
            .temp-big { font-size: 2rem; }
            .grid-2 { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
<div class="terminal">
    <div class="header">⧩ WEATHER :: TERMINAL v1.0</div>

    <div class="row">
        <input id="zipInput" placeholder="ZIP (e.g., 43065)" value="">
        <button class="btn" onclick="fetchByZip()">► GET ZIP</button>
        <button class="btn btn-loc" onclick="fetchByLocation()">◉ MY LOC</button>
    </div>

    <div id="content">
        <div class="card loading">[ READY ] Enter ZIP or tap MY LOC</div>
    </div>
    <div class="footer">[ openweathermap.org :: free tier ]</div>
</div>

<script>
function fetchWeather(lat, lon) {
    document.getElementById('content').innerHTML = '<div class="card loading">[ FETCHING ... ]</div>';
    fetch(`/api/weather?lat=${lat}&lon=${lon}`)
        .then(r => r.json())
        .then(data => {
            if (data.error) throw new Error(data.error);
            let html = '';
            const c = data.current;
            // Current
            html += `<div class="card">
                <div style="display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;">
                    <div><span class="temp-big">${c.temp}°C</span> <span class="dim">feels ${c.feels_like}°C</span></div>
                    <div style="text-align:right;">${c.description.toUpperCase()}<br><span class="dim">HUM ${c.humidity}% · PRESS ${c.pressure}hPa</span></div>
                </div>
                <div class="grid-2" style="margin-top:10px;">
                    <div>WIND ${c.wind_speed} m/s</div>
                    <div>CLOUDS ${c.clouds}%</div>
                    <div>VISIBILITY ${(c.visibility/1000).toFixed(1)} km</div>
                    <div>SUNR ${c.sunrise.slice(11,16)} UTC · SUNS ${c.sunset.slice(11,16)} UTC</div>
                </div>
            </div>`;
            // Hourly
            html += `<div class="card"><div style="font-weight:bold;margin-bottom:6px;">◈ NEXT 12H</div><div class="grid-3">`;
            data.hourly.slice(0,12).forEach(h => {
                html += `<div class="hour-item">${h.time.slice(11,16)}<br><strong>${h.temp}°</strong><br><span class="dim">${h.description.slice(0,12)}</span><br><span class="rain">☔ ${(h.pop*100).toFixed(0)}%</span> <span class="wind">💨${h.wind_speed}</span></div>`;
            });
            html += `</div></div>`;
            // Daily
            html += `<div class="card"><div style="font-weight:bold;margin-bottom:6px;">◈ 7-DAY</div><div class="grid-3">`;
            data.daily.forEach(d => {
                html += `<div class="day-item">${d.date.slice(5)}<br><strong>${d.temp_day}°</strong> <span class="dim">/${d.temp_night}°</span><br><span class="dim">${d.description.slice(0,12)}</span><br><span class="rain">☔ ${(d.pop*100).toFixed(0)}%</span></div>`;
            });
            html += `</div></div>`;
            document.getElementById('content').innerHTML = html;
        })
        .catch(err => document.getElementById('content').innerHTML = `<div class="card error">[ ERROR ] ${err.message}</div>`);
}

function fetchByZip() {
    const zip = document.getElementById('zipInput').value.trim();
    if (!zip) { alert('Enter ZIP'); return; }
    fetch(`/api/zip?zip=${zip}`)
        .then(r => r.json())
        .then(data => {
            if (data.error) throw new Error(data.error);
            fetchWeather(data.lat, data.lon);
        })
        .catch(err => document.getElementById('content').innerHTML = `<div class="card error">[ ZIP ERROR ] ${err.message}</div>`);
}

function fetchByLocation() {
    if (!navigator.geolocation) {
        alert('Geolocation not supported');
        return;
    }
    navigator.geolocation.getCurrentPosition(
        pos => fetchWeather(pos.coords.latitude, pos.coords.longitude),
        err => document.getElementById('content').innerHTML = `<div class="card error">[ LOC ERROR ] ${err.message}</div>`
    );
}
</script>
</body>
</html>
"""

def geocode_zip(zip_code):
    url = f"http://api.openweathermap.org/geo/1.0/zip?zip={zip_code},US&appid={API_KEY}"
    resp = requests.get(url, timeout=10).json()
    if "lat" not in resp:
        url2 = f"http://api.openweathermap.org/geo/1.0/zip?zip={zip_code}&appid={API_KEY}"
        resp2 = requests.get(url2, timeout=10).json()
        if "lat" not in resp2:
            raise ValueError(f"ZIP not found: {zip_code}")
        return resp2["lat"], resp2["lon"]
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
