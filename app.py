# -*- coding: utf-8 -*-
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

subscriptions = []

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
    <link rel="manifest" href="/manifest.json">
    <title>Weather Hub</title>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        :root {
            --bg: #0a0e14; --text: #e8edf3; --card-bg: rgba(255,255,255,0.04);
            --border: rgba(255,255,255,0.06); --accent: #4a8eff; --secondary: #6a7b8f;
            --shadow: rgba(0,0,0,0.4); --radius: 32px; --font: -apple-system, sans-serif;
        }
        body { background:var(--bg); color:var(--text); font-family:var(--font); padding:16px; display:flex; justify-content:center; }
        .app { max-width:500px; width:100%; }
        .theme-bar { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:14px; justify-content:center; }
        .theme-btn { padding:5px 12px; border-radius:20px; border:1px solid var(--border); background:var(--card-bg); color:var(--text); font-size:0.75rem; cursor:pointer; transition:0.2s; }
        .theme-btn.active, .theme-btn:hover { background:var(--accent); color:#fff; border-color:var(--accent); }
        .header { display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid var(--border); margin-bottom:14px; cursor:default; user-select:none; }
        .header h1 { font-size:1.4rem; }
        .header button { background:var(--card-bg); border:1px solid var(--border); color:var(--secondary); font-size:1.1rem; padding:5px 10px; border-radius:20px; cursor:pointer; transition:0.2s; margin-left:4px; }
        .header button:hover { background:var(--accent); color:#fff; }
        .search-row { display:flex; gap:6px; margin-bottom:14px; }
        .search-row input { flex:1; background:var(--card-bg); border:1px solid var(--border); border-radius:30px; padding:10px 16px; color:var(--text); font-size:0.95rem; outline:none; }
        .search-row input:focus { border-color:var(--accent); }
        .search-row button { background:var(--accent); border:none; border-radius:30px; padding:10px 16px; color:#fff; font-weight:600; font-size:0.85rem; cursor:pointer; transition:0.2s; }
        .search-row button:hover { filter:brightness(1.1); }
        .search-row .loc-btn { background:var(--card-bg); color:var(--text); border:1px solid var(--border); }
        .search-row .loc-btn:hover { background:var(--accent); color:#fff; }
        .notify-btn { background:var(--card-bg); border:1px solid var(--border); border-radius:30px; padding:8px; width:100%; text-align:center; cursor:pointer; transition:0.2s; margin-bottom:12px; font-size:0.8rem; }
        .notify-btn:hover { background:var(--accent); color:#fff; }
        .notify-status { font-size:0.7rem; color:var(--secondary); text-align:center; margin-top:4px; }
        .alert-banner { background:rgba(255,200,50,0.12); border:1px solid #ffcc44; border-radius:16px; padding:10px 14px; margin-bottom:14px; display:none; cursor:pointer; transition:0.2s; }
        .alert-banner:hover { background:rgba(255,200,50,0.2); }
        .alert-banner .title { font-weight:600; color:#ffcc44; }
        .alert-banner .desc { font-size:0.8rem; color:var(--secondary); }
        .loc-manager { background:var(--card-bg); border-radius:16px; padding:12px; margin-bottom:14px; border:1px solid var(--border); }
        .loc-manager .row { display:flex; gap:6px; margin-bottom:8px; }
        .loc-manager .row input { flex:1; padding:8px 12px; border-radius:20px; border:1px solid var(--border); background:var(--bg); color:var(--text); }
        .loc-manager .row button { padding:8px 16px; border-radius:20px; border:none; background:var(--accent); color:#fff; cursor:pointer; }
        .loc-tags { display:flex; flex-wrap:wrap; gap:6px; }
        .loc-tag { background:var(--glass); padding:4px 12px; border-radius:20px; font-size:0.8rem; display:flex; align-items:center; gap:6px; border:1px solid var(--border); }
        .loc-tag .del { cursor:pointer; opacity:0.6; }
        .loc-tag .del:hover { opacity:1; color:#ff6b6b; }
        .card { background:var(--card-bg); backdrop-filter:blur(20px); border-radius:var(--radius); padding:20px; margin-bottom:16px; border:1px solid var(--border); box-shadow:0 8px 32px var(--shadow); transition:0.2s; }
        .card:hover { transform:scale(1.01); }
        .temp-row { display:flex; justify-content:space-between; align-items:center; }
        .temp-main { font-size:3.8rem; font-weight:300; letter-spacing:-2px; line-height:1; }
        .temp-main small { font-size:1.6rem; font-weight:300; color:var(--secondary); }
        .condition { font-size:1.1rem; font-weight:500; margin:4px 0 2px; }
        .high-low { font-size:0.95rem; color:var(--secondary); }
        .details { display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; margin-top:14px; padding-top:14px; border-top:1px solid var(--border); }
        .detail { text-align:center; }
        .detail .label { font-size:0.65rem; text-transform:uppercase; color:var(--secondary); letter-spacing:0.5px; }
        .detail .value { font-size:1rem; font-weight:500; margin-top:2px; }
        .section-title { display:flex; justify-content:space-between; align-items:baseline; margin:16px 0 8px; padding:0 4px; }
        .section-title h3 { font-size:0.95rem; font-weight:600; color:var(--secondary); }
        .hourly { display:flex; overflow-x:auto; gap:12px; padding:6px 4px 14px; scroll-snap-type:x mandatory; -webkit-overflow-scrolling:touch; }
        .hourly::-webkit-scrollbar { height:3px; background:transparent; }
        .hourly::-webkit-scrollbar-thumb { background:var(--secondary); border-radius:4px; }
        .hour-item { flex:0 0 65px; text-align:center; background:var(--card-bg); border-radius:18px; padding:8px 4px; border:1px solid var(--border); scroll-snap-align:start; cursor:pointer; transition:0.2s; }
        .hour-item:hover { background:var(--accent); border-color:var(--accent); transform:scale(1.05); }
        .hour-item .time { font-size:0.7rem; color:var(--secondary); }
        .hour-item .temp { font-size:1.1rem; font-weight:500; margin:2px 0; }
        .hour-item .icon { font-size:1.2rem; }
        .hour-item .pop { font-size:0.65rem; color:var(--accent); }
        .daily { display:flex; flex-direction:column; gap:4px; margin-top:6px; }
        .day-item { display:flex; justify-content:space-between; align-items:center; background:var(--card-bg); padding:10px 14px; border-radius:14px; border:1px solid var(--border); transition:0.15s; }
        .day-item:hover { background:var(--glass); }
        .day-item .day-name { font-weight:500; width:60px; font-size:0.9rem; }
        .day-item .day-icon { font-size:1.1rem; width:36px; text-align:center; }
        .day-item .day-temps .high { color:var(--text); }
        .day-item .day-temps .low { color:var(--secondary); margin-left:6px; }
        .day-item .day-pop { font-size:0.75rem; color:var(--accent); width:45px; text-align:right; }
        .modal { display:none; position:fixed; inset:0; background:rgba(0,0,0,0.7); backdrop-filter:blur(4px); justify-content:center; align-items:center; z-index:1000; }
        .modal.active { display:flex; }
        .modal-content { background:var(--bg); border:1px solid var(--border); border-radius:32px; padding:28px 24px; max-width:340px; width:90%; box-shadow:0 20px 60px rgba(0,0,0,0.8); }
        .modal-content h2 { font-size:1.4rem; margin-bottom:12px; }
        .modal-content p { margin:6px 0; font-size:0.95rem; color:var(--secondary); }
        .modal-content .close { margin-top:16px; background:var(--accent); border:none; border-radius:30px; padding:10px; color:#fff; font-weight:600; cursor:pointer; width:100%; }
        .modal-content .close:hover { filter:brightness(1.1); }
        .loading { text-align:center; padding:30px 0; color:var(--secondary); }
        .error { background:rgba(255,70,70,0.08); border:1px solid rgba(255,70,70,0.2); border-radius:16px; padding:16px; color:#ff7a7a; text-align:center; }
        .debug { background:rgba(0,0,0,0.3); border-radius:10px; padding:6px 10px; font-size:0.6rem; color:#4a6a5a; margin-top:16px; max-height:60px; overflow-y:auto; display:none; font-family:monospace; border:1px solid var(--border); }
        .admin { background:var(--card-bg); border:1px solid var(--border); border-radius:16px; padding:16px; margin-top:16px; display:none; }
        .admin h4 { font-size:0.9rem; margin-bottom:8px; color:var(--accent); }
        .admin .row { display:flex; gap:6px; flex-wrap:wrap; align-items:center; margin-bottom:6px; }
        .admin input { background:var(--bg); border:1px solid var(--border); color:var(--text); padding:6px 10px; border-radius:12px; flex:1; min-width:100px; font-size:0.8rem; }
        .admin button { background:var(--card-bg); border:1px solid var(--border); color:var(--text); padding:6px 14px; border-radius:20px; cursor:pointer; font-size:0.75rem; transition:0.2s; }
        .admin button:hover { background:var(--accent); color:#fff; }
        .admin .log { background:rgba(0,0,0,0.2); border-radius:8px; padding:8px; font-size:0.65rem; max-height:100px; overflow-y:auto; font-family:monospace; color:var(--secondary); white-space:pre-wrap; }
        @media (max-width:480px) { .temp-main { font-size:3rem; } .details { grid-template-columns:1fr 1fr; } }
    </style>
</head>
<body>
<div class="app">

<!-- Theme bar -->
<div class="theme-bar">
    <button class="theme-btn active" data-theme="dark">Dark</button>
    <button class="theme-btn" data-theme="light">Light</button>
    <button class="theme-btn" data-theme="retro">Retro</button>
    <button class="theme-btn" data-theme="lightning">Lightning</button>
</div>

<!-- Header (triple-click for admin) -->
<div class="header" id="headerTitle">
    <h1>⛅ Weather Hub</h1>
    <div>
        <button onclick="getLocation()" title="My Location">📍</button>
        <button onclick="refreshAll()" title="Refresh All">⟳</button>
    </div>
</div>

<!-- Location manager -->
<div class="loc-manager">
    <div class="row">
        <input id="newZip" placeholder="Add ZIP (e.g., 43065)" value="">
        <button onclick="addZip()">➕ Add</button>
    </div>
    <div class="loc-tags" id="zipTags"></div>
</div>

<!-- Notifications -->
<button class="notify-btn" onclick="subscribePush()">🔔 Enable Notifications</button>
<div class="notify-status" id="notifyStatus">Get severe weather alerts via push</div>

<!-- Alert banner -->
<div class="alert-banner" id="alertBanner" onclick="showAlertModal()">
    <div class="title" id="alertTitle">⚠️ Weather Alert</div>
    <div class="desc" id="alertDesc">Click for details</div>
</div>

<!-- Weather content -->
<div id="content"><div class="loading">Add a ZIP or tap location</div></div>

<!-- Modals -->
<div class="modal" id="hourModal">
    <div class="modal-content">
        <h2 id="modalTitle">Hour Detail</h2>
        <p id="modalBody">Loading...</p>
        <button class="close" onclick="closeModal()">Close</button>
    </div>
</div>
<div class="modal" id="alertModal">
    <div class="modal-content">
        <h2>⚠️ NWS Alerts</h2>
        <div id="alertBody"></div>
        <button class="close" onclick="closeAlertModal()">Close</button>
    </div>
</div>

<!-- Admin panel -->
<div class="admin" id="adminPanel">
    <h4>🛠️ Admin Panel</h4>
    <div class="row">
        <input id="customPushTitle" placeholder="Push Title" value="Custom Message">
        <input id="customPushBody" placeholder="Push Body" value="This is a test push.">
        <button onclick="sendCustomPush()">📲 Send</button>
    </div>
    <div style="display:flex; gap:6px; flex-wrap:wrap; margin-top:6px;">
        <button onclick="testAlert()">🔔 Test Alert</button>
        <button onclick="refreshAll()">🔄 Refresh All</button>
        <button onclick="clearLogs()">🗑️ Clear Log</button>
    </div>
    <div class="log" id="adminLog">Ready.</div>
</div>

<div class="debug" id="debug"></div>

<script>
// ===== THEMES =====
const themes = {
    dark: {
        '--bg': '#0a0e14', '--text': '#e8edf3', '--card-bg': 'rgba(255,255,255,0.04)',
        '--border': 'rgba(255,255,255,0.06)', '--accent': '#4a8eff', '--secondary': '#6a7b8f',
        '--shadow': 'rgba(0,0,0,0.4)', '--radius': '32px', '--font': '-apple-system, sans-serif'
    },
    light: {
        '--bg': '#f2f5f9', '--text': '#1a202c', '--card-bg': 'rgba(255,255,255,0.7)',
        '--border': 'rgba(0,0,0,0.08)', '--accent': '#007aff', '--secondary': '#6a7b8f',
        '--shadow': 'rgba(0,0,0,0.08)', '--radius': '32px', '--font': '-apple-system, sans-serif'
    },
    retro: {
        '--bg': '#0a0f0a', '--text': '#33ff33', '--card-bg': 'rgba(0,20,0,0.5)',
        '--border': '#33ff33', '--accent': '#33ff33', '--secondary': '#4f8f4f',
        '--shadow': 'rgba(51,255,51,0.2)', '--radius': '12px', '--font': '"Courier New", monospace'
    },
    lightning: {
        '--bg': '#0a0a12', '--text': '#b8c7ff', '--card-bg': 'rgba(30,40,80,0.4)',
        '--border': '#6a7aff', '--accent': '#8a9aff', '--secondary': '#5a6a9f',
        '--shadow': 'rgba(100,120,255,0.2)', '--radius': '20px', '--font': '"Segoe UI", sans-serif'
    }
};

function applyTheme(name) {
    const theme = themes[name];
    if (!theme) return;
    const root = document.documentElement;
    for (let [k, v] of Object.entries(theme)) root.style.setProperty(k, v);
    document.querySelectorAll('.theme-btn').forEach(b => b.classList.toggle('active', b.dataset.theme === name));
    localStorage.setItem('theme', name);
}
document.querySelectorAll('.theme-btn').forEach(b => b.addEventListener('click', () => applyTheme(b.dataset.theme)));
applyTheme(localStorage.getItem('theme') || 'dark');

// ===== STATE =====
let zipList = JSON.parse(localStorage.getItem('zips') || '[]');
let hourlyMap = {};
let currentAlerts = [];
let clickCount = 0, clickTimer = null;

// ===== ADMIN TOGGLE (triple-click header) =====
document.getElementById('headerTitle').addEventListener('click', function() {
    clickCount++;
    clearTimeout(clickTimer);
    clickTimer = setTimeout(() => { clickCount = 0; }, 500);
    if (clickCount === 3) {
        document.getElementById('adminPanel').style.display =
            document.getElementById('adminPanel').style.display === 'block' ? 'none' : 'block';
        adminLog('Admin toggled');
        clickCount = 0;
    }
});

function adminLog(msg) {
    const log = document.getElementById('adminLog');
    log.textContent += new Date().toLocaleTimeString() + ' :: ' + msg + '\n';
    log.scrollTop = log.scrollHeight;
}
function logDebug(msg) {
    const el = document.getElementById('debug');
    el.style.display = 'block';
    el.innerHTML += new Date().toLocaleTimeString() + ' :: ' + msg + '<br>';
    el.scrollTop = el.scrollHeight;
    adminLog('DEBUG: ' + msg);
}
function showLoading(text) {
    document.getElementById('content').innerHTML = '<div class="loading">⏳ ' + text + '</div>';
}
function showError(msg) {
    document.getElementById('content').innerHTML = '<div class="error">⚠️ ' + msg + '</div>';
    logDebug('ERROR: ' + msg);
}
function icon(desc) {
    const d = desc.toLowerCase();
    if (d.includes('clear')) return '☀️';
    if (d.includes('cloud')) return '☁️';
    if (d.includes('rain')) return '🌧️';
    if (d.includes('thunder')) return '⛈️';
    if (d.includes('snow')) return '❄️';
    if (d.includes('mist') || d.includes('fog')) return '🌫️';
    return '🌤️';
}
function formatDay(iso) {
    const days = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
    return days[new Date(iso + 'T00:00:00Z').getUTCDay()];
}

// ===== ZIP MANAGEMENT =====
function saveZips() {
    localStorage.setItem('zips', JSON.stringify(zipList));
    renderTags();
}
function renderTags() {
    const c = document.getElementById('zipTags');
    if (zipList.length === 0) { c.innerHTML = '<span style="opacity:0.5;font-size:0.8rem;">No ZIPs added.</span>'; return; }
    c.innerHTML = zipList.map(z => `<span class="loc-tag">${z} <span class="del" onclick="removeZip('${z}')">✕</span></span>`).join('');
}
window.addZip = function() {
    const inp = document.getElementById('newZip');
    const z = inp.value.trim();
    if (!z) return alert('Enter ZIP');
    if (zipList.includes(z)) return alert('Already added');
    zipList.push(z);
    saveZips();
    inp.value = '';
    refreshAll();
};
window.removeZip = function(z) {
    zipList = zipList.filter(x => x !== z);
    saveZips();
    refreshAll();
};

// ===== FETCH HELPERS =====
function fetchWeatherForZip(zip) {
    return fetch('/api/zip?zip=' + zip)
        .then(r => r.json())
        .then(data => {
            if (data.error) throw new Error(data.error);
            return fetch('/api/weather?lat=' + data.lat + '&lon=' + data.lon)
                .then(r => r.json())
                .then(w => {
                    if (w.error) throw new Error(w.error);
                    return fetch('/api/nws?lat=' + data.lat + '&lon=' + data.lon)
                        .then(r => r.json())
                        .then(a => ({ weather: w, alerts: a.alerts || [], zip: zip }));
                });
        });
}

// ===== REFRESH ALL =====
window.refreshAll = function() {
    if (zipList.length === 0) {
        document.getElementById('content').innerHTML = '<div class="loading">Add a ZIP to see weather</div>';
        return;
    }
    showLoading('Fetching ' + zipList.length + ' locations...');
    Promise.all(zipList.map(z => fetchWeatherForZip(z).catch(err => ({ error: err.message, zip: z }))))
        .then(results => {
            let combined = [];
            let html = '';
            results.forEach(res => {
                if (res.error) {
                    html += `<div class="card" style="border-color:#ff6b6b;"><strong>${res.zip}</strong> — Error: ${res.error}</div>`;
                    return;
                }
                const w = res.weather;
                const alerts = res.alerts;
                if (alerts.length) combined = combined.concat(alerts.map(a => ({ ...a, zip: res.zip })));
                html += renderCard(w, res.zip);
            });
            document.getElementById('content').innerHTML = html;
            // Alerts
            if (combined.length) {
                currentAlerts = combined;
                const banner = document.getElementById('alertBanner');
                banner.style.display = 'block';
                document.getElementById('alertTitle').textContent = '⚠️ ' + combined.length + ' Alert(s)';
                document.getElementById('alertDesc').textContent = combined[0].headline || combined[0].event;
                if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
                    navigator.serviceWorker.ready.then(reg => {
                        reg.showNotification('⚠️ Weather Alert', {
                            body: combined[0].headline || combined[0].event,
                            icon: '/icon.png',
                            tag: 'nws-alert'
                        });
                    });
                }
            } else {
                document.getElementById('alertBanner').style.display = 'none';
                currentAlerts = [];
            }
            logDebug('Refreshed ' + zipList.length + ' locations');
            adminLog('Refreshed all');
        })
        .catch(err => showError('Refresh failed: ' + err.message));
};

// ===== RENDER CARD =====
function renderCard(data, zip) {
    const c = data.current;
    const hourly = data.hourly;
    const daily = data.daily;
    hourlyMap[zip] = hourly;

    let html = `<div class="card" data-zip="${zip}">`;
    html += `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
        <strong style="font-size:1.2rem;">📍 ${zip}</strong>
        <span style="font-size:0.8rem;color:var(--secondary);">${c.description}</span>
    </div>`;
    html += `<div class="temp-row"><div>
        <div class="temp-main">${Math.round(c.temp)}°<small>F</small></div>
        <div class="high-low">H: ${Math.round(c.temp_max)}° · L: ${Math.round(c.temp_min)}°</div>
    </div><div style="font-size:3.8rem;">${icon(c.description)}</div></div>`;

    html += `<div class="details">`;
    html += `<div class="detail"><div class="label">Feels Like</div><div class="value">${Math.round(c.feels_like)}°</div></div>`;
    html += `<div class="detail"><div class="label">Humidity</div><div class="value">${c.humidity}%</div></div>`;
    html += `<div class="detail"><div class="label">Wind</div><div class="value">${Math.round(c.wind_speed)} mph</div></div>`;
    html += `<div class="detail"><div class="label">Pressure</div><div class="value">${c.pressure} hPa</div></div>`;
    html += `<div class="detail"><div class="label">UV Index</div><div class="value">${c.uvi || '—'}</div></div>`;
    html += `<div class="detail"><div class="label">Visibility</div><div class="value">${(c.visibility/1609).toFixed(1)} mi</div></div>`;
    html += `</div>`;

    html += `<div style="margin-top:10px; font-size:0.75rem; color:var(--secondary); display:flex; justify-content:space-between;">
        <span>☀️ Rise ${c.sunrise.slice(11,16)}</span>
        <span>🌇 Set ${c.sunset.slice(11,16)}</span>
    </div>`;

    // Hourly
    html += `<div class="section-title" style="margin-top:12px;"><h3>Hourly</h3><span>click for details</span></div>`;
    html += `<div class="hourly">`;
    hourly.slice(0,8).forEach((h, idx) => {
        html += `<div class="hour-item" onclick="showHour('${zip}',${idx})">
            <div class="time">${h.time.slice(11,16)}</div>
            <div class="icon">${icon(h.description)}</div>
            <div class="temp">${Math.round(h.temp)}°</div>
            <div class="pop">${h.pop > 0 ? Math.round(h.pop*100)+'%' : ''}</div>
        </div>`;
    });
    html += `</div>`;

    // Daily
    html += `<div class="section-title"><h3>5-Day Forecast</h3></div><div class="daily">`;
    daily.forEach(d => {
        const dayName = (d.date === new Date().toISOString().slice(0,10)) ? 'Today' : formatDay(d.date);
        html += `<div class="day-item">
            <span class="day-name">${dayName}</span>
            <span class="day-icon">${icon(d.description)}</span>
            <span class="day-temps"><span class="high">${Math.round(d.temp_max)}°</span><span class="low">${Math.round(d.temp_min)}°</span></span>
            <span class="day-pop">${d.pop > 0 ? Math.round(d.pop*100)+'%' : ''}</span>
        </div>`;
    });
    html += `</div>`;

    html += `</div>`;
    return html;
}

// ===== HOURLY MODAL =====
function showHour(zip, idx) {
    const h = hourlyMap[zip] && hourlyMap[zip][idx];
    if (!h) return;
    const modal = document.getElementById('hourModal');
    document.getElementById('modalTitle').textContent = '🕒 ' + h.time.slice(11,16) + ' (' + zip + ')';
    let body = '';
    body += '<p><strong>Temp:</strong> ' + Math.round(h.temp) + '°F</p>';
    body += '<p><strong>Condition:</strong> ' + h.description + '</p>';
    body += '<p><strong>Rain chance:</strong> ' + Math.round(h.pop*100) + '%</p>';
    body += '<p><strong>Wind:</strong> ' + Math.round(h.wind_speed) + ' mph</p>';
    body += '<p><strong>Humidity:</strong> ' + (h.humidity || '—') + '%</p>';
    if (h.pop > 0.5) {
        const est = Math.round((h.pop * 2) * 10) / 10;
        body += '<p><strong>🌧 Rain expected to last:</strong> ~' + est + ' hours</p>';
    } else {
        body += '<p><strong>☀️ No significant rain expected</strong></p>';
    }
    document.getElementById('modalBody').innerHTML = body;
    modal.classList.add('active');
}
function closeModal() { document.getElementById('hourModal').classList.remove('active'); }

// ===== ALERT MODAL =====
function showAlertModal() {
    if (currentAlerts.length === 0) return;
    const modal = document.getElementById('alertModal');
    let html = '';
    currentAlerts.forEach(a => {
        html += `<div style="margin-bottom:12px; border-bottom:1px solid var(--border); padding-bottom:8px;">
            <strong>${a.event}</strong> <span style="font-size:0.7rem;color:var(--secondary);">(${a.zip || ''})</span><br>
            <span style="font-size:0.8rem;color:var(--secondary);">${a.headline || ''}</span><br>
            <span style="font-size:0.75rem;">${a.description ? a.description.slice(0,200)+'...' : ''}</span>
        </div>`;
    });
    document.getElementById('alertBody').innerHTML = html;
    modal.classList.add('active');
}
function closeAlertModal() { document.getElementById('alertModal').classList.remove('active'); }

// ===== LOCATION (GPS) =====
window.getLocation = function() {
    if (!navigator.geolocation) { alert('Geolocation not supported'); return; }
    navigator.geolocation.getCurrentPosition(
        pos => {
            showLoading('Getting your location...');
            fetch('/api/weather?lat=' + pos.coords.latitude + '&lon=' + pos.coords.longitude)
                .then(r => r.json())
                .then(data => {
                    if (data.error) throw new Error(data.error);
                    const dummy = '📍 My Location';
                    const card = renderCard(data, dummy);
                    document.getElementById('content').innerHTML = card + document.getElementById('content').innerHTML;
                    logDebug('Added current location');
                })
                .catch(err => showError('Location error: ' + err.message));
        },
        err => showError('Geolocation error: ' + err.message)
    );
};

// ===== FETCH ZIP =====
window.fetchZip = function() {
    const zip = document.getElementById('zipInput').value.trim();
    if (!zip) return alert('Enter ZIP');
    // Add to list if not present
    if (!zipList.includes(zip)) {
        zipList.push(zip);
        saveZips();
    }
    refreshAll();
};

// ===== ADMIN: TEST ALERT =====
window.testAlert = function() {
    const test = [{
        event: 'Test Alert',
        headline: 'Simulated NWS alert for testing',
        description: 'No actual warning exists.',
        zip: 'TEST'
    }];
    currentAlerts = test;
    const banner = document.getElementById('alertBanner');
    banner.style.display = 'block';
    document.getElementById('alertTitle').textContent = '⚠️ TEST Alert';
    document.getElementById('alertDesc').textContent = 'Simulated – click for details';
    adminLog('Test alert shown');
    if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
        navigator.serviceWorker.ready.then(reg => {
            reg.showNotification('⚠️ TEST Alert', { body: 'This is a test push.', icon: '/icon.png', tag: 'test' });
        });
    }
};

// ===== ADMIN: CUSTOM PUSH =====
window.sendCustomPush = function() {
    const title = document.getElementById('customPushTitle').value || 'Custom';
    const body = document.getElementById('customPushBody').value || 'Test';
    if (!('serviceWorker' in navigator) || !navigator.serviceWorker.controller) {
        alert('Enable notifications first');
        return;
    }
    navigator.serviceWorker.ready.then(reg => {
        reg.showNotification(title, { body: body, icon: '/icon.png', tag: 'custom' });
        adminLog('Custom push sent: ' + title);
    });
};

// ===== PUSH NOTIFICATIONS =====
const VAPID_PUBLIC_KEY = 'BPtmgQv8hflZW4VYcjZV7QgVry8NSMddcBuoB53mzLZdrhYO81oKlpS1XW0I9zwxxj63qSJD_6DvMkekYqqf7XY';

function subscribePush() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        document.getElementById('notifyStatus').textContent = '❌ Push not supported';
        return;
    }
    navigator.serviceWorker.register('/sw.js')
        .then(reg => {
            return reg.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY)
            });
        })
        .then(sub => {
            fetch('/api/subscribe', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(sub) })
                .then(r => r.json())
                .then(() => {
                    document.getElementById('notifyStatus').textContent = '✅ Notifications enabled';
                    logDebug('Subscribed');
                    adminLog('Push subscribed');
                });
        })
        .catch(err => {
            document.getElementById('notifyStatus').textContent = '❌ ' + err.message;
            logDebug('Push error: ' + err.message);
        });
}
function urlBase64ToUint8Array(b64) {
    const padding = '='.repeat((4 - b64.length % 4) % 4);
    const base64 = (b64 + padding).replace(/-/g, '+').replace(/_/g, '/');
    const raw = window.atob(base64);
    const out = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
    return out;
}

if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js')
        .then(() => logDebug('SW registered'))
        .catch(err => logDebug('SW reg error: ' + err));
}

window.clearLogs = function() {
    document.getElementById('adminLog').textContent = 'Cleared.';
    document.getElementById('debug').innerHTML = '';
    document.getElementById('debug').style.display = 'none';
};

window.onload = function() {
    renderTags();
    if (zipList.length) refreshAll();
    else document.getElementById('content').innerHTML = '<div class="loading">Add a ZIP or tap location</div>';
    adminLog('App loaded with ' + zipList.length + ' ZIPs');
};
</script>
</body>
</html>
"""

# ===== FLASK ROUTES =====
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
    sw_js = """
self.addEventListener('install', e => e.waitUntil(self.skipWaiting()));
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('push', e => {
    const data = e.data ? e.data.json() : {title: '⚠️ Weather Alert', body: 'Check your weather'};
    e.waitUntil(
        self.registration.showNotification(data.title || '⚠️ Weather Alert', {
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
        return jsonify(get_weather_data(float(lat), float(lon)))
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

# ===== BACKEND HELPERS =====
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
    seen = set()
    for item in fore["list"]:
        date_str = datetime.fromtimestamp(item["dt"], tz=timezone.utc).isoformat()[:10]
        if date_str not in seen and len(daily) < 5:
            seen.add(date_str)
            daily.append({
                "date": date_str,
                "temp_max": item["main"]["temp_max"],
                "temp_min": item["main"]["temp_min"],
                "description": item["weather"][0]["description"],
                "pop": item.get("pop", 0.0)
            })
    return {"current": current, "hourly": hourly, "daily": daily}

def get_nws_alerts(lat, lon):
    headers = {
        "User-Agent": "WeatherHub/1.0 (scottvrrr@gmail.com)",
        "Accept": "application/json"
    }
    try:
        point = requests.get(f"https://api.weather.gov/points/{lat},{lon}", headers=headers, timeout=10)
        if point.status_code != 200:
            return []
        alerts_url = point.json().get("properties", {}).get("alerts")
        if not alerts_url:
            return []
        resp = requests.get(alerts_url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return []
        features = resp.json().get("features", [])
        return [{
            "event": f.get("properties", {}).get("event", "Unknown"),
            "headline": f.get("properties", {}).get("headline", ""),
            "description": f.get("properties", {}).get("description", ""),
            "severity": f.get("properties", {}).get("severity", ""),
            "effective": f.get("properties", {}).get("effective", "")
        } for f in features]
    except Exception as e:
        app.logger.error(f"NWS exception: {str(e)}")
        return []

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
