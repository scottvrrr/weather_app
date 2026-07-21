# 90s theme
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
logging.basicConfig(level=logging.INFO)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>WEATHER::TERMINAL v2.0</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        /* 90s CRT green on black */
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #0a0f0a;
            color: #33ff33;
            font-family: 'Courier New', Courier, 'VT323', monospace;
            padding: 16px;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            text-shadow: 0 0 8px #33ff3366;
        }
        .terminal {
            max-width: 860px;
            width: 100%;
            background: #0c120c;
            border: 3px solid #33ff33;
            border-radius: 16px;
            padding: 24px 22px;
            box-shadow: 0 0 40px #33ff3344, inset 0 0 30px #33ff3311;
            position: relative;
        }
        /* Scanline effect (very subtle) */
        .terminal::after {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: repeating-linear-gradient(0deg, rgba(0,0,0,0.03) 0px, rgba(0,0,0,0.03) 2px, transparent 2px, transparent 4px);
            pointer-events: none;
            border-radius: 16px;
        }
        .header {
            font-size: 1.8rem;
            font-weight: bold;
            letter-spacing: 4px;
            border-bottom: 2px dashed #33ff33;
            padding-bottom: 10px;
            margin-bottom: 20px;
            text-align: center;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            flex-wrap: wrap;
        }
        .header span { opacity: 0.6; font-size: 1rem; letter-spacing: 1px; }
        .row {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 20px;
        }
        .row input {
            flex: 2;
            min-width: 160px;
            background: #0f140f;
            border: 2px solid #33ff33;
            color: #33ff33;
            font-family: 'Courier New', Courier, monospace;
            font-size: 1.1rem;
            padding: 12px 14px;
            border-radius: 8px;
            outline: none;
            transition: 0.1s;
            text-shadow: 0 0 4px #33ff3344;
        }
        .row input::placeholder { color: #1f4f1f; opacity: 0.8; }
        .row input:focus { border-color: #66ff66; background: #0f1a0f; box-shadow: 0 0 16px #33ff3344; }
        .btn {
            background: #0f140f;
            border: 2px solid #33ff33;
            color: #33ff33;
            font-family: 'Courier New', Courier, monospace;
            font-size: 1.1rem;
            padding: 12px 22px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.15s;
            flex: 1;
            min-width: 110px;
            text-align: center;
            text-shadow: 0 0 4px #33ff3344;
        }
        .btn:hover {
            background: #1f3f1f;
            box-shadow: 0 0 24px #33ff3366;
            transform: scale(1.02);
        }
        .btn-loc { border-color: #33ccff; color: #33ccff; text-shadow: 0 0 4px #33ccff44; }
        .btn-loc:hover { background: #1f2f3f; box-shadow: 0 0 24px #33ccff66; }
        .card {
            border: 2px solid #33ff33;
            border-radius: 10px;
            padding: 16px 14px;
            margin-top: 16px;
            background: #0c120c;
            box-shadow: inset 0 0 20px #33ff3308;
        }
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 24px; }
        .grid-3 { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px,1fr)); gap: 12px; margin-top: 12px; }
        .hour-item, .day-item {
            border: 1px solid #1f4f1f;
            border-radius: 8px;
            padding: 10px 6px;
            text-align: center;
            background: #0a120a;
            font-size: 0.9rem;
            transition: 0.1s;
        }
        .hour-item:hover, .day-item:hover { border-color: #33ff33; background: #0f1a0f; }
        .temp-big { font-size: 3.2rem; font-weight: bold; letter-spacing: 2px; line-height: 1; }
        .dim { opacity: 0.6; }
        .rain { color: #66ddff; }
        .wind { color: #88dd88; }
        .loading { opacity: 0.6; text-align: center; padding: 30px; }
        .error { color: #ff6666; border-color: #ff6666; }
        .footer {
            margin-top: 18px;
            font-size: 0.75rem;
            opacity: 0.4;
            text-align: center;
            border-top: 1px dashed #1f3f1f;
            padding-top: 14px;
            letter-spacing: 1px;
        }
        .debug-box {
            background: #0a120a;
            border: 1px solid #1f4f1f;
            border-radius: 6px;
            padding: 8px 10px;
            font-size: 0.7rem;
            color: #4f8f4f;
            margin-top: 12px;
            max-height: 120px;
            overflow-y: auto;
            display: none;
            font-family: 'Courier New', monospace;
        }
        .debug-box::-webkit-scrollbar { width: 6px; background: #0a120a; }
        .debug-box::-webkit-scrollbar-thumb { background: #1f4f1f; border-radius: 4px; }
        .blink { animation: blink 1.2s step-end infinite; }
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
        @media (max-width: 480px) {
            .row input { min-width: 100px; font-size: 0.95rem; }
            .btn { min-width: 70px; font-size: 0.9rem; padding: 10px 12px; }
            .temp-big { font-size: 2.4rem; }
            .grid-2 { grid-template-columns: 1fr; }
            .header { font-size: 1.4rem; }
        }
    </style>
</head>
<body>
<div class="terminal">
    <div class="header">
        <span>⧩ WEATHER::TERMINAL</span>
        <span>v2.0 <span class="blink">█</span></span>
    </div>

    <div class="row">
        <input id="zipInput" placeholder="ZIP (e.g., 43065)" value="">
        <button class="btn" onclick="fetchByZip()">► GET ZIP</button>
        <button class="btn btn-loc" onclick="fetchByLocation()">◉ MY LOC</button>
    </div>

    <div id="content">
        <div class="card loading">[ READY ] Enter ZIP or tap MY LOC</div>
    </div>

    <div id="debug" class="debug-box"></div>
    <div class="footer">[ OpenWeatherMap :: Free Tier ]</div>
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
        document.getElementById('content').innerHTML = `<div class="card loading">[ ${text} ]</div>`;
    }

    function showError(msg) {
        document.getElementById('content').innerHTML = `<div class="card error">⚠️ ERROR :: ${msg}</div>`;
        logDebug('ERROR: ' + msg);
    }

    function renderWeather(data) {
        let html = '';
        const c = data.current;
        // Current
        html += `<div class="card">
            <div style="display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;">
                <div><span class="temp-big">${Math.round(c.temp)}°C</span> <span class="dim">feels ${Math.round(c.feels_like)}°C</span></div>
                <div style="text-align:right;font-size:1.2rem;">${c.description.toUpperCase()}<br><span class="dim">HUM ${c.humidity}% · PRESS ${c.pressure}hPa</span></div>
            </div>
            <div class="grid-2" style="margin-top:12px;">
                <div>💨 WIND ${c.wind_speed} m/s</div>
                <div>☁️ CLOUDS ${c.clouds}%</div>
                <div>👁 VISIBILITY ${(c.visibility/1000).toFixed(1)} km</div>
                <div>🌅 ${c.sunrise.slice(11,16)} UTC · 🌇 ${c.sunset.slice(11,16)} UTC</div>
            </div>
            <div style="margin-top:8px; font-size:0.85rem; border-top:1px dashed #1f3f1f; padding-top:8px;">
                <span class="dim">SUNRISE · ${c.sunrise.slice(0,10)} ${c.sunrise.slice(11,19)}</span>
                <span style="margin-left:16px;" class="dim">SUNSET · ${c.sunset.slice(0,10)} ${c.sunset.slice(11,19)}</span>
            </div>
        </div>`;

        // Hourly (next 24h in 3h steps)
        html += `<div class="card"><div style="font-weight:bold;margin-bottom:8px;">◈ NEXT 24H (3H STEPS)</div><div class="grid-3">`;
        data.hourly.slice(0,8).forEach(h => {
            html += `<div class="hour-item">${h.time.slice(11,16)}<br><strong>${Math.round(h.temp)}°</strong><br><span class="dim">${h.description.slice(0,14)}</span><br><span class="rain">☔ ${(h.pop*100).toFixed(0)}%</span> <span class="wind">💨${Math.round(h.wind_speed)}</span></div>`;
        });
        html += `</div></div>`;

        // Daily (5 days)
        html += `<div class="card"><div style="font-weight:bold;margin-bottom:8px;">◈ 5-DAY FORECAST</div><div class="grid-3">`;
        data.daily.forEach(d => {
            html += `<div class="day-item">${d.date.slice(5)}<br><strong>${Math.round(d.temp_day)}°</strong> <span class="dim">/${Math.round(d.temp_night)}°</span><br><span class="dim">${d.description.slice(0,14)}</span><br><span class="rain">☔ ${(d.pop*100).toFixed(0)}%</span></div>`;
        });
        html += `</div></div>`;

        document.getElementById('content').innerHTML = html;
        logDebug('Display updated');
    }

    function fetchWeather(lat, lon) {
        logDebug('Fetching lat='+lat.toFixed(5)+' lon='+lon.toFixed(5));
        showLoading('FETCHING WEATHER ...');
        fetch(`/api/weather?lat=${lat}&lon=${lon}`)
            .then(r => r.json())
            .then(data => {
                if (data.error) throw new Error(data.error);
                renderWeather(data);
            })
            .catch(err => {
                logDebug('Weather error: '+err.message);
                showError(err.message);
            });
    }

    window.fetchByZip = function() {
        const zip = document.getElementById('zipInput').value.trim();
        if (!zip) { alert('ENTER ZIP'); return; }
        logDebug('ZIP: '+zip);
        showLoading('LOOKUP ZIP ...');
        fetch(`/api/zip?zip=${zip}`)
            .then(r => r.json())
            .then(data => {
                if (data.error) throw new Error(data.error);
                logDebug('ZIP resolved -> lat='+data.lat+' lon='+data.lon);
                fetchWeather(data.lat, data.lon);
            })
            .catch(err => {
                logDebug('ZIP error: '+err.message);
                showError('ZIP: '+err.message);
            });
    };

    window.fetchByLocation = function() {
        logDebug('Requesting geolocation');
        if (!navigator.geolocation) {
            alert('Geolocation not supported');
            return;
        }
        showLoading('GETTING LOCATION ...');
        navigator.geolocation.getCurrentPosition(
            pos => {
                logDebug('Location OK');
                fetchWeather(pos.coords.latitude, pos.coords.longitude);
            },
            err => {
                logDebug('Geolocation error: '+err.message);
                showError('Location: '+err.message);
            }
        );
    };

    // Auto load a default ZIP (NYC) for demo, but we don't auto-fetch.
    // User must click.
    logDebug('Terminal ready. Enter ZIP or tap MY LOC.');
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
    # Current
    url_curr = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    curr_resp = requests.get(url_curr, timeout=10)
    curr = curr_resp.json()
    if curr_resp.status_code != 200:
        raise ValueError(f"Weather API error: {curr.get('message', 'Unknown')}")
    
    # 5-day forecast (3-hour steps)
    url_fore = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    fore_resp = requests.get(url_fore, timeout=10)
    fore = fore_resp.json()
    if fore_resp.status_code != 200:
        raise ValueError(f"Forecast API error: {fore.get('message', 'Unknown')}")

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
    
    # Hourly (8 items = 24 hours)
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
                "temp_day": item["main"]["temp_max"],
                "temp_night": item["main"]["temp_min"],
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
