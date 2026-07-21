# app.py - Full interactive weather with push notifications, themes, NWS alerts
import requests
import os
import json
import logging
from flask import Flask, render_template_string, request, jsonify, send_file
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import threading
import time

load_dotenv()
API_KEY = os.getenv("OWM_API_KEY")
if not API_KEY:
    raise ValueError("OWM_API_KEY not set")

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# In-memory store for subscription (for demo – use DB in production)
subscriptions = []

# ---------- HTML with all features ----------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Weather Hub</title>
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
    <link rel="manifest" href="/manifest.json">
    <style id="theme-style">
        /* Default: Apple Dark */
        :root {
            --bg: #0a0e14;
            --text: #e8edf3;
            --card-bg: rgba(255,255,255,0.04);
            --border: rgba(255,255,255,0.06);
            --accent: #4a8eff;
            --secondary: #6a7b8f;
            --glass: rgba(255,255,255,0.03);
            --shadow: rgba(0,0,0,0.4);
            --card-radius: 32px;
            --font: -apple-system, 'Helvetica Neue', sans-serif;
            --transition: 0.3s;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: var(--bg);
            color: var(--text);
            font-family: var(--font);
            padding: 16px;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            transition: background var(--transition), color var(--transition);
        }
        .app { max-width: 500px; width: 100%; margin: 0 auto; }
        /* Theme bar */
        .theme-bar {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            margin-bottom: 14px;
            justify-content: center;
        }
        .theme-btn {
            padding: 5px 12px;
            border-radius: 20px;
            border: 1px solid var(--border);
            background: var(--card-bg);
            color: var(--text);
            font-size: 0.75rem;
            cursor: pointer;
            transition: 0.2s;
            font-weight: 500;
        }
        .theme-btn:hover { background: var(--accent); color: white; border-color: var(--accent); }
        .theme-btn.active { background: var(--accent); color: white; border-color: var(--accent); }
        /* Header */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid var(--border);
            margin-bottom: 14px;
        }
        .header h1 { font-size: 1.4rem; font-weight: 600; letter-spacing: -0.5px; }
        .header-actions button {
            background: var(--card-bg);
            border: 1px solid var(--border);
            color: var(--secondary);
            font-size: 1.1rem;
            padding: 5px 10px;
            border-radius: 20px;
            cursor: pointer;
            transition: 0.2s;
            margin-left: 4px;
        }
        .header-actions button:hover { background: var(--accent); color: white; }
        /* Search */
        .search-row {
            display: flex;
            gap: 6px;
            margin-bottom: 14px;
        }
        .search-row input {
            flex: 1;
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 30px;
            padding: 10px 16px;
            color: var(--text);
            font-size: 0.95rem;
            outline: none;
            transition: 0.2s;
        }
        .search-row input::placeholder { color: var(--secondary); }
        .search-row input:focus { border-color: var(--accent); }
        .search-row button {
            background: var(--accent);
            border: none;
            border-radius: 30px;
            padding: 10px 16px;
            color: white;
            font-weight: 600;
            font-size: 0.85rem;
            cursor: pointer;
            transition: 0.2s;
        }
        .search-row button:hover { filter: brightness(1.1); }
        .search-row .loc-btn { background: var(--card-bg); color: var(--text); border: 1px solid var(--border); }
        .search-row .loc-btn:hover { background: var(--accent); color: white; }
        /* Notify button */
        .notify-btn {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 30px;
            padding: 8px 16px;
            color: var(--text);
            font-size: 0.8rem;
            cursor: pointer;
            transition: 0.2s;
            margin-bottom: 12px;
            width: 100%;
            text-align: center;
        }
        .notify-btn:hover { background: var(--accent); color: white; }
        /* Alert banner */
        .alert-banner {
            background: rgba(255,200,50,0.12);
            border: 1px solid #ffcc44;
            border-radius: 16px;
            padding: 10px 14px;
            margin-bottom: 14px;
            display: none;
            cursor: pointer;
            transition: 0.2s;
        }
        .alert-banner:hover { background: rgba(255,200,50,0.2); }
        .alert-banner .alert-title { font-weight: 600; color: #ffcc44; }
        .alert-banner .alert-desc { font-size: 0.8rem; color: var(--secondary); }
        /* Current card */
        .current-card {
            background: var(--card-bg);
            backdrop-filter: blur(20px);
            border-radius: var(--card-radius);
            padding: 20px 18px;
            margin-bottom: 16px;
            border: 1px solid var(--border);
            box-shadow: 0 8px 32px var(--shadow);
            transition: background var(--transition);
        }
        .temp-row { display: flex; justify-content: space-between; align-items: center; }
        .temp-main { font-size: 3.8rem; font-weight: 300; letter-spacing: -2px; line-height: 1; }
        .temp-main small { font-size: 1.6rem; font-weight: 300; color: var(--secondary); }
        .condition-text { font-size: 1.1rem; font-weight: 500; margin: 4px 0 2px; }
        .high-low { font-size: 0.95rem; color: var(--secondary); }
        .extra-details {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 10px;
            margin-top: 14px;
            padding-top: 14px;
            border-top: 1px solid var(--border);
        }
        .extra-detail { text-align: center; }
        .extra-detail .label { font-size: 0.65rem; text-transform: uppercase; color: var(--secondary); letter-spacing: 0.5px; }
        .extra-detail .value { font-size: 1rem; font-weight: 500; margin-top: 2px; }
        /* Hourly scroll - clickable items */
        .section-title {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin: 16px 0 8px;
            padding: 0 4px;
        }
        .section-title h3 { font-size: 0.95rem; font-weight: 600; color: var(--secondary); letter-spacing: 0.3px; }
        .hourly-scroll {
            display: flex;
            overflow-x: auto;
            gap: 12px;
            padding: 6px 4px 14px;
            scroll-snap-type: x mandatory;
            -webkit-overflow-scrolling: touch;
        }
        .hourly-scroll::-webkit-scrollbar { height: 3px; background: transparent; }
        .hourly-scroll::-webkit-scrollbar-thumb { background: var(--secondary); border-radius: 4px; }
        .hour-item {
            flex: 0 0 65px;
            text-align: center;
            background: var(--card-bg);
            border-radius: 18px;
            padding: 8px 4px;
            border: 1px solid var(--border);
            scroll-snap-align: start;
            cursor: pointer;
            transition: 0.2s;
        }
        .hour-item:hover { background: var(--accent); border-color: var(--accent); transform: scale(1.05); }
        .hour-item .time { font-size: 0.7rem; color: var(--secondary); }
        .hour-item .temp { font-size: 1.1rem; font-weight: 500; margin: 2px 0; }
        .hour-item .icon { font-size: 1.2rem; }
        .hour-item .pop { font-size: 0.65rem; color: var(--accent); }
        /* Daily list */
        .daily-list {
            display: flex;
            flex-direction: column;
            gap: 4px;
            margin-top: 6px;
        }
        .day-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--card-bg);
            padding: 10px 14px;
            border-radius: 14px;
            border: 1px solid var(--border);
            transition: 0.15s;
        }
        .day-item:hover { background: var(--glass); }
        .day-item .day-name { font-weight: 500; width: 60px; font-size: 0.9rem; }
        .day-item .day-icon { font-size: 1.1rem; width: 36px; text-align: center; }
        .day-item .day-temps .high { color: var(--text); }
        .day-item .day-temps .low { color: var(--secondary); margin-left: 6px; }
        .day-item .day-pop { font-size: 0.75rem; color: var(--accent); width: 45px; text-align: right; }
        /* Modal for hour detail */
        .modal {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.7);
            backdrop-filter: blur(4px);
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        .modal.active { display: flex; }
        .modal-content {
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 32px;
            padding: 28px 24px;
            max-width: 340px;
            width: 90%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.8);
            color: var(--text);
        }
        .modal-content h2 { font-size: 1.4rem; margin-bottom: 12px; }
        .modal-content p { margin: 6px 0; font-size: 0.95rem; color: var(--secondary); }
        .modal-content .close-btn {
            margin-top: 16px;
            background: var(--accent);
            border: none;
            border-radius: 30px;
            padding: 10px 20px;
            color: white;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
        }
        .modal-content .close-btn:hover { filter: brightness(1.1); }
        /* States */
        .loading-state { text-align: center; padding: 30px 0; color: var(--secondary); }
        .error-state { background: rgba(255,70,70,0.08); border: 1px solid rgba(255,70,70,0.2); border-radius: 16px; padding: 16px; color: #ff7a7a; text-align: center; }
        .debug-box {
            background: rgba(0,0,0,0.3);
            border-radius: 10px;
            padding: 6px 10px;
            font-size: 0.6rem;
            color: #4a6a5a;
            margin-top: 16px;
            max-height: 60px;
            overflow-y: auto;
            display: none;
            font-family: monospace;
            border: 1px solid var(--border);
        }
        /* Notification permission */
        .notify-status { font-size: 0.7rem; color: var(--secondary); text-align: center; margin-top: 4px; }
        @media (max-width: 480px) {
            .temp-main { font-size: 3rem; }
            .extra-details { grid-template-columns: 1fr 1fr; }
        }
    </style>
</head>
<body>
<div class="app">
    <!-- Theme Bar -->
    <div class="theme-bar">
        <button class="theme-btn active" data-theme="apple-dark">🍎 Dark</button>
        <button class="theme-btn" data-theme="apple-light">🍎 Light</button>
        <button class="theme-btn" data-theme="retro">🖥 Retro</button>
        <button class="theme-btn" data-theme="lightning">⚡ Lightning</button>
    </div>

    <!-- Header -->
    <div class="header">
        <h1>⛅ Weather Hub</h1>
        <div class="header-actions">
            <button onclick="fetchByLocation()" title="My Location">📍</button>
            <button onclick="refreshWeather()" title="Refresh">⟳</button>
        </div>
    </div>

    <!-- Search -->
    <div class="search-row">
        <input id="zipInput" placeholder="ZIP code (e.g., 43065)" value="">
        <button onclick="fetchByZip()">Search</button>
        <button class="loc-btn" onclick="fetchByLocation()">📍</button>
    </div>

    <!-- Push notification subscription -->
    <button class="notify-btn" id="notifyBtn" onclick="subscribePush()">🔔 Enable Notifications</button>
    <div class="notify-status" id="notifyStatus">Tap to get alerts for severe weather</div>

    <!-- NWS Alert Banner -->
    <div class="alert-banner" id="alertBanner" onclick="showAlertModal()">
        <div class="alert-title" id="alertTitle">⚠️ Weather Alert</div>
        <div class="alert-desc" id="alertDesc">Click for details</div>
    </div>

    <!-- Main content -->
    <div id="content">
        <div class="loading-state">Enter a ZIP or tap location</div>
    </div>

    <!-- Modal for hourly detail -->
    <div class="modal" id="hourModal">
        <div class="modal-content">
            <h2 id="modalTitle">Hour Detail</h2>
            <p id="modalBody">Loading...</p>
            <button class="close-btn" onclick="closeModal()">Close</button>
        </div>
    </div>

    <!-- Modal for alert detail -->
    <div class="modal" id="alertModal">
        <div class="modal-content">
            <h2>⚠️ NWS Alert</h2>
            <div id="alertBody"></div>
            <button class="close-btn" onclick="closeAlertModal()">Close</button>
        </div>
    </div>

    <div class="debug-box" id="debug"></div>
</div>

<script>
// ========== THEMES ==========
const themes = {
    'apple-dark': {
        '--bg': '#0a0e14',
        '--text': '#e8edf3',
        '--card-bg': 'rgba(255,255,255,0.04)',
        '--border': 'rgba(255,255,255,0.06)',
        '--accent': '#4a8eff',
        '--secondary': '#6a7b8f',
        '--shadow': 'rgba(0,0,0,0.4)',
        '--card-radius': '32px',
        '--font': '-apple-system, "Helvetica Neue", sans-serif'
    },
    'apple-light': {
        '--bg': '#f2f5f9',
        '--text': '#1a202c',
        '--card-bg': 'rgba(255,255,255,0.7)',
        '--border': 'rgba(0,0,0,0.08)',
        '--accent': '#007aff',
        '--secondary': '#6a7b8f',
        '--shadow': 'rgba(0,0,0,0.08)',
        '--card-radius': '32px',
        '--font': '-apple-system, "Helvetica Neue", sans-serif'
    },
    'retro': {
        '--bg': '#0a0f0a',
        '--text': '#33ff33',
        '--card-bg': 'rgba(0,20,0,0.5)',
        '--border': '#33ff33',
        '--accent': '#33ff33',
        '--secondary': '#4f8f4f',
        '--shadow': 'rgba(51,255,51,0.2)',
        '--card-radius': '12px',
        '--font': '"Courier New", monospace',
        '--transition': '0.1s'
    },
    'lightning': {
        '--bg': '#0a0a12',
        '--text': '#b8c7ff',
        '--card-bg': 'rgba(30,40,80,0.4)',
        '--border': '#6a7aff',
        '--accent': '#8a9aff',
        '--secondary': '#5a6a9f',
        '--shadow': 'rgba(100,120,255,0.2)',
        '--card-radius': '20px',
        '--font': '"Segoe UI", sans-serif'
    }
};

function applyTheme(name) {
    const theme = themes[name];
    if (!theme) return;
    const root = document.documentElement;
    for (let [key, val] of Object.entries(theme)) {
        root.style.setProperty(key, val);
    }
    // Mark active button
    document.querySelectorAll('.theme-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.theme === name);
    });
    localStorage.setItem('weatherTheme', name);
}

document.querySelectorAll('.theme-btn').forEach(btn => {
    btn.addEventListener('click', () => applyTheme(btn.dataset.theme));
});
// Load saved theme
const saved = localStorage.getItem('weatherTheme') || 'apple-dark';
applyTheme(saved);

// ========== STATE ==========
let currentLat = null;
let currentLon = null;
let hourlyData = []; // store for modal

// ========== DEBUG ==========
function logDebug(msg) {
    const el = document.getElementById('debug');
    el.style.display = 'block';
    el.innerHTML += new Date().toLocaleTimeString() + ' :: ' + msg + '<br>';
    el.scrollTop = el.scrollHeight;
}

// ========== UI HELPERS ==========
function showLoading(text) {
    document.getElementById('content').innerHTML = `<div class="loading-state">⏳ ${text}</div>`;
}
function showError(msg) {
    document.getElementById('content').innerHTML = `<div class="error-state">⚠️ ${msg}</div>`;
    logDebug('ERROR: ' + msg);
}
function getIcon(desc) {
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

// ========== RENDER ==========
function renderWeather(data) {
    const c = data.current;
    const hourly = data.hourly;
    const daily = data.daily;
    hourlyData = hourly; // store for modal

    let html = '';
    // Current
    html += `<div class="current-card">
        <div class="temp-row">
            <div>
                <div class="temp-main">${Math.round(c.temp)}°<small>F</small></div>
                <div class="condition-text">${c.description}</div>
                <div class="high-low">H: ${Math.round(c.temp_max)}° · L: ${Math.round(c.temp_min)}°</div>
            </div>
            <div style="font-size:3.8rem;">${getIcon(c.description)}</div>
        </div>
        <div class="extra-details">
            <div class="extra-detail"><div class="label">Feels Like</div><div class="value">${Math.round(c.feels_like)}°</div></div>
            <div class="extra-detail"><div class="label">Humidity</div><div class="value">${c.humidity}%</div></div>
            <div class="extra-detail"><div class="label">Wind</div><div class="value">${Math.round(c.wind_speed)} mph</div></div>
            <div class="extra-detail"><div class="label">Pressure</div><div class="value">${c.pressure} hPa</div></div>
            <div class="extra-detail"><div class="label">UV Index</div><div class="value">${c.uvi !== undefined ? c.uvi : '—'}</div></div>
            <div class="extra-detail"><div class="label">Visibility</div><div class="value">${(c.visibility / 1609).toFixed(1)} mi</div></div>
        </div>
        <div style="margin-top:10px; font-size:0.75rem; color:var(--secondary); display:flex; justify-content:space-between;">
            <span>☀️ Rise ${c.sunrise.slice(11,16)}</span>
            <span>🌇 Set ${c.sunset.slice(11,16)}</span>
        </div>
    </div>`;

    // Hourly scroll (clickable)
    html += `<div class="section-title"><h3>Hourly</h3><span>click for details</span></div>
    <div class="hourly-scroll">`;
    hourly.slice(0,8).forEach((h, idx) => {
        html += `<div class="hour-item" onclick="showHourDetail(${idx})">
            <div class="time">${h.time.slice(11,16)}</div>
            <div class="icon">${getIcon(h.description)}</div>
            <div class="temp">${Math.round(h.temp)}°</div>
            <div class="pop">${h.pop > 0 ? Math.round(h.pop*100)+'%' : ''}</div>
        </div>`;
    });
    html += `</div>`;

    // Daily
    html += `<div class="section-title"><h3>5-Day Forecast</h3></div><div class="daily-list">`;
    daily.forEach(d => {
        const dayName = d.date === new Date().toISOString().slice(0,10) ? 'Today' : formatDay(d.date);
        html += `<div class="day-item">
            <span class="day-name">${dayName}</span>
            <span class="day-icon">${getIcon(d.description)}</span>
            <span class="day-temps"><span class="high">${Math.round(d.temp_max)}°</span><span class="low">${Math.round(d.temp_min)}°</span></span>
            <span class="day-pop">${d.pop > 0 ? Math.round(d.pop*100)+'%' : ''}</span>
        </div>`;
    });
    html += `</div>`;

    document.getElementById('content').innerHTML = html;
    logDebug('Display updated');
}

// ========== MODAL FOR HOUR DETAIL ==========
function showHourDetail(idx) {
    const h = hourlyData[idx];
    if (!h) return;
    const modal = document.getElementById('hourModal');
    document.getElementById('modalTitle').textContent = `⏰ ${h.time.slice(11,16)}`;
    let body = `
        <p><strong>Temp:</strong> ${Math.round(h.temp)}°F</p>
        <p><strong>Condition:</strong> ${h.description}</p>
        <p><strong>Rain chance:</strong> ${Math.round(h.pop*100)}%</p>
        <p><strong>Wind:</strong> ${Math.round(h.wind_speed)} mph</p>
        <p><strong>Humidity:</strong> ${h.humidity !== undefined ? h.humidity+'%' : '—'}</p>
    `;
    // If rain > 50%, estimate duration (dummy logic)
    if (h.pop > 0.5) {
        const est = Math.round((h.pop * 2) * 10) / 10;
        body += `<p><strong>🌧 Rain expected to last:</strong> ~${est} hours</p>`;
    } else {
        body += `<p><strong>☀️ No significant rain expected</strong></p>`;
    }
    document.getElementById('modalBody').innerHTML = body;
    modal.classList.add('active');
}
function closeModal() {
    document.getElementById('hourModal').classList.remove('active');
}

// ========== NWS ALERTS ==========
let currentAlerts = [];
function fetchAlerts(lat, lon) {
    fetch(`/api/nws?lat=${lat}&lon=${lon}`)
        .then(r => r.json())
        .then(data => {
            if (data.alerts && data.alerts.length > 0) {
                currentAlerts = data.alerts;
                const banner = document.getElementById('alertBanner');
                banner.style.display = 'block';
                document.getElementById('alertTitle').textContent = `⚠️ ${data.alerts.length} Alert(s)`;
                document.getElementById('alertDesc').textContent = data.alerts[0].headline || data.alerts[0].event;
                // Trigger notification if subscribed
                if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
                    navigator.serviceWorker.ready.then(reg => {
                        reg.showNotification('Weather Alert', {
                            body: data.alerts[0].headline || data.alerts[0].event,
                            icon: '/icon.png',
                            tag: 'nws-alert'
                        });
                    });
                }
            } else {
                document.getElementById('alertBanner').style.display = 'none';
            }
        })
        .catch(err => logDebug('NWS error: ' + err.message));
}
function showAlertModal() {
    if (currentAlerts.length === 0) return;
    const modal = document.getElementById('alertModal');
    let html = '';
    currentAlerts.forEach(a => {
        html += `<div style="margin-bottom:12px; border-bottom:1px solid var(--border); padding-bottom:8px;">
            <strong>${a.event}</strong><br>
            <span style="font-size:0.8rem;color:var(--secondary);">${a.headline || ''}</span><br>
            <span style="font-size:0.75rem;">${a.description ? a.description.slice(0,200)+'...' : ''}</span>
        </div>`;
    });
    document.getElementById('alertBody').innerHTML = html;
    modal.classList.add('active');
}
function closeAlertModal() {
    document.getElementById('alertModal').classList.remove('active');
}

// ========== WEATHER FETCH ==========
function fetchWeather(lat, lon) {
    currentLat = lat; currentLon = lon;
    logDebug('Fetching lat='+lat.toFixed(4)+' lon='+lon.toFixed(4));
    showLoading('Fetching weather...');
    fetch(`/api/weather?lat=${lat}&lon=${lon}`)
        .then(r => r.json())
        .then(data => {
            if (data.error) throw new Error(data.error);
            renderWeather(data);
            fetchAlerts(lat, lon);
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

window.refreshWeather = function() {
    if (currentLat && currentLon) {
        fetchWeather(currentLat, currentLon);
    } else {
        fetchByLocation();
    }
};

// ========== PUSH NOTIFICATIONS ==========
function subscribePush() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        document.getElementById('notifyStatus').textContent = '❌ Push not supported';
        return;
    }
    navigator.serviceWorker.register('/sw.js')
        .then(reg => reg.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array('YOUR_VAPID_PUBLIC_KEY') // replace with real key
        }))
        .then(sub => {
            // Send subscription to server
            fetch('/api/subscribe', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(sub)
            }).then(res => res.json()).then(data => {
                document.getElementById('notifyStatus').textContent = '✅ Notifications enabled';
                logDebug('Subscribed');
            });
        })
        .catch(err => {
            document.getElementById('notifyStatus').textContent = '❌ ' + err.message;
            logDebug('Push error: '+err.message);
        });
}

// Helper for VAPID key
function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

// Service worker registration
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js')
        .then(() => logDebug('SW registered'))
        .catch(err => logDebug('SW reg error: '+err));
}

// Auto-load location on start
window.onload = function() {
    fetchByLocation();
};
</script>
</body>
</html>
"""

# ---------- BACKEND ROUTES ----------
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/manifest.json')
def manifest():
    return {
        "name": "Weather Hub",
        "short_name": "Weather",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0a0e14",
        "theme_color": "#0a0e14",
        "icons": [{"src": "/icon.png", "sizes": "192x192", "type": "image/png"}]
    }

@app.route('/sw.js')
def sw():
    # Simple service worker that caches and handles push
    sw_js = """
self.addEventListener('install', e => e.waitUntil(self.skipWaiting()));
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('push', e => {
    const data = e.data ? e.data.json() : {title: 'Weather Alert', body: 'Check your weather'};
    e.waitUntil(
        self.registration.showNotification(data.title || 'Weather Alert', {
            body: data.body || 'Severe weather possible',
            icon: '/icon.png',
            tag: 'weather-alert'
        })
    );
});
self.addEventListener('notificationclick', e => {
    e.notification.close();
    e.waitUntil(clients.openWindow('/'));
});
"""
    return sw_js, 200, {'Content-Type': 'application/javascript'}

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

@app.route('/api/nws')
def api_nws():
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    if not lat or not lon:
        return jsonify({"error": "Missing lat/lon"}), 400
    try:
        alerts = get_nws_alerts(float(lat), float(lon))
        return jsonify({"alerts": alerts})
    except Exception as e:
        app.logger.error(f"NWS error: {str(e)}")
        return jsonify({"alerts": [], "error": str(e)}), 500

@app.route('/api/subscribe', methods=['POST'])
def subscribe():
    sub = request.json
    if sub:
        subscriptions.append(sub)
        app.logger.info(f"Subscription added: {len(subscriptions)} total")
        return jsonify({"status": "ok"})
    return jsonify({"error": "Invalid"}), 400

# ---------- BACKEND FUNCTIONS ----------
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
    url_curr = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=imperial"
    curr_resp = requests.get(url_curr, timeout=10)
    curr = curr_resp.json()
    if curr_resp.status_code != 200:
        raise ValueError(f"Weather API error: {curr.get('message', 'Unknown')}")
    
    url_fore = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=imperial"
    fore_resp = requests.get(url_fore, timeout=10)
    fore = fore_resp.json()
    if fore_resp.status_code != 200:
        raise ValueError(f"Forecast API error: {fore.get('message', 'Unknown')}")

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
        "uvi": None
    }
    
    hourly = []
    for item in fore["list"][:8]:
        hourly.append({
            "time": datetime.fromtimestamp(item["dt"], tz=timezone.utc).isoformat(),
            "temp": item["main"]["temp"],
            "description": item["weather"][0]["description"],
            "pop": item.get("pop", 0.0),
            "wind_speed": item["wind"]["speed"],
            "humidity": item["main"]["humidity"]
        })
    
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

def get_nws_alerts(lat, lon):
    # NWS API: point metadata
    point_url = f"https://api.weather.gov/points/{lat},{lon}"
    point_resp = requests.get(point_url, headers={"User-Agent": "WeatherApp/1.0"})
    if point_resp.status_code != 200:
        return []
    point_data = point_resp.json()
    alerts_url = point_data.get("properties", {}).get("alerts")
    if not alerts_url:
        return []
    alerts_resp = requests.get(alerts_url, headers={"User-Agent": "WeatherApp/1.0"})
    if alerts_resp.status_code != 200:
        return []
    alerts_data = alerts_resp.json()
    features = alerts_data.get("features", [])
    result = []
    for f in features:
        props = f.get("properties", {})
        result.append({
            "event": props.get("event", "Unknown"),
            "headline": props.get("headline", ""),
            "description": props.get("description", ""),
            "severity": props.get("severity", ""),
            "effective": props.get("effective", "")
        })
    return result

# ---------- BACKGROUND THREAD FOR PUSH NOTIFICATIONS (simulated) ----------
def alert_pusher():
    """Periodically check for alerts and push to all subscribers (simplified)"""
    # In production, you'd use a proper scheduler and only push when new alerts appear.
    # This is a demo placeholder.
    pass

# ---------- RUN ----------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
