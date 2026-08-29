#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template_string, request, jsonify
from flask_cors import CORS
import requests
import json
import re
import time
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

app = Flask(__name__)
CORS(app)

# ============ БАЗА САЙТОВ ============
WEBSITES_DB = {
    "Instagram": {"url": "https://www.instagram.com/{}/", "country": "🇺🇸 USA", "category": "social"},
    "Twitter": {"url": "https://twitter.com/{}", "country": "🇺🇸 USA", "category": "social"},
    "Facebook": {"url": "https://www.facebook.com/{}", "country": "🇺🇸 USA", "category": "social"},
    "VK": {"url": "https://vk.com/{}", "country": "🇷🇺 Russia", "category": "social"},
    "Odnoklassniki": {"url": "https://ok.ru/{}", "country": "🇷🇺 Russia", "category": "social"},
    "YouTube": {"url": "https://www.youtube.com/@{}", "country": "🇺🇸 USA", "category": "social"},
    "TikTok": {"url": "https://www.tiktok.com/@{}", "country": "🇨🇳 China", "category": "social"},
    "Reddit": {"url": "https://www.reddit.com/user/{}", "country": "🇺🇸 USA", "category": "social"},
    "GitHub": {"url": "https://github.com/{}", "country": "🇺🇸 USA", "category": "dev"},
    "Telegram": {"url": "https://t.me/{}", "country": "🇷🇺 Russia", "category": "messenger"},
    "Discord": {"url": "https://discord.com/users/{}", "country": "🇺🇸 USA", "category": "messenger"},
    "Habr": {"url": "https://habr.com/ru/users/{}/", "country": "🇷🇺 Russia", "category": "forum"},
    "Pikabu": {"url": "https://pikabu.ru/@{}", "country": "🇷🇺 Russia", "category": "forum"},
    "Twitch": {"url": "https://www.twitch.tv/{}", "country": "🇺🇸 USA", "category": "stream"},
    "LinkedIn": {"url": "https://www.linkedin.com/in/{}/", "country": "🇺🇸 USA", "category": "prof"},
    "Medium": {"url": "https://medium.com/@{}", "country": "🇺🇸 USA", "category": "blog"},
    "Steam": {"url": "https://steamcommunity.com/id/{}", "country": "🇺🇸 USA", "category": "gaming"},
    "SoundCloud": {"url": "https://soundcloud.com/{}", "country": "🇩🇪 Germany", "category": "music"},
    "Pinterest": {"url": "https://www.pinterest.com/{}/", "country": "🇺🇸 USA", "category": "media"},
    "Spotify": {"url": "https://open.spotify.com/user/{}", "country": "🇸🇪 Sweden", "category": "music"},
}

# ============ ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ============
scan_logs = []
scan_results = []
scan_breaches = []
is_scanning = False
stop_scan = False


# ============ ФУНКЦИИ ============
def add_log(msg, color='white'):
    scan_logs.append({'msg': msg, 'color': color})


def check_breaches(email):
    """Проверка утечек через Have I Been Pwned"""
    results = []
    try:
        resp = requests.get(
            f'https://haveibeenpwned.com/api/v3/breachedaccount/{email}',
            timeout=10,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        if resp.status_code == 200:
            breaches = resp.json()
            for b in breaches[:10]:
                results.append({
                    'name': b.get('Name', 'Unknown'),
                    'date': b.get('BreachDate', 'Unknown'),
                    'desc': b.get('Description', '')[:100]
                })
    except Exception as e:
        print(f"Ошибка проверки утечек: {e}")
    return results


def check_site(site_name, site_data, username):
    """Проверка одного сайта"""
    if stop_scan:
        return None
    try:
        url = site_data["url"].format(username=username)
        resp = requests.get(url, timeout=3, allow_redirects=True)
        if resp.status_code == 200:
            text = resp.text.lower()
            if "not found" not in text and "doesn't exist" not in text and "page not found" not in text:
                return {
                    "name": site_name,
                    "url": url,
                    "country": site_data.get("country", "Unknown"),
                    "category": site_data.get("category", "other")
                }
    except:
        pass
    return None


def scan_username(username):
    """Поиск по username с многопоточностью"""
    global stop_scan, scan_logs
    results = []
    total = len(WEBSITES_DB)
    checked = 0

    add_log(f"[+] Начинаю поиск по никнейму: {username}", 'blue')
    add_log(f"[+] Всего сайтов: {total}", 'blue')

    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {}
        for name, data in WEBSITES_DB.items():
            if stop_scan:
                break
            futures[executor.submit(check_site, name, data, username)] = name

        for future in as_completed(futures):
            if stop_scan:
                break
            checked += 1
            result = future.result()
            if result:
                results.append(result)
                add_log(f"  ✅ {result['name']}: {result['url']}", 'green')
            else:
                # Показываем только если мало сайтов
                if checked <= 10:
                    site_name = futures[future]
                    add_log(f"  ❌ {site_name}: не найден", 'red')

            # Показываем прогресс каждые 5 сайтов
            if checked % 5 == 0:
                add_log(f"  ⏳ Прогресс: {checked}/{total}", 'blue')

    if not stop_scan:
        add_log(f"[✓] Поиск завершен! Найдено: {len(results)}", 'green')
    else:
        add_log("[!] Поиск прерван", 'yellow')

    return results


# ============ HTML ШАБЛОН ============
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>SNOOP PRO v2.0 - OSINT Tool</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f0f23;
            color: #d4d4d4;
            padding: 10px;
            min-height: 100vh;
        }
        .container { max-width: 500px; margin: 0 auto; }

        .logo {
            background: #0f0f23;
            padding: 8px 0;
            margin-bottom: 10px;
            text-align: center;
        }
        .logo-text {
            font-family: 'Courier New', monospace;
            font-size: 9px;
            line-height: 1.3;
            color: #ff6b6b;
            white-space: pre;
            text-align: center;
            display: inline-block;
        }
        .logo-text .g { color: #51cf66; }
        .logo-text .b { color: #4dabf7; }
        .logo-text .y { color: #ffd43b; }

        .info-bar {
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
            padding: 4px 0;
            font-size: 10px;
            justify-content: center;
            background: #0f0f23;
        }
        .info-bar .version { color: #ffd43b; font-weight: bold; }
        .info-bar .mode { color: #ff922b; }
        .info-bar .db { color: #4dabf7; }
        .info-bar .modules { color: #cc5de8; }

        .search-box {
            background: #1a1a2e;
            border-radius: 10px;
            padding: 12px;
            margin-bottom: 10px;
            border: 1px solid #2a2a3e;
        }
        .search-row {
            display: flex;
            gap: 8px;
            margin-bottom: 8px;
        }
        .search-row input {
            flex: 1;
            padding: 10px 12px;
            background: #0f0f23;
            border: 1px solid #2a2a3e;
            border-radius: 8px;
            color: #d4d4d4;
            font-size: 14px;
            outline: none;
            min-height: 44px;
        }
        .search-row input:focus { border-color: #4dabf7; }
        .search-row input::placeholder { color: #555; font-size: 12px; }

        .btn {
            padding: 10px 14px;
            border: none;
            border-radius: 8px;
            font-size: 12px;
            font-weight: bold;
            color: white;
            cursor: pointer;
            transition: all 0.2s;
            text-align: center;
            min-height: 44px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 4px;
        }
        .btn:active { transform: scale(0.95); opacity: 0.8; }
        .btn-primary { background: #339af0; }
        .btn-danger { background: #f03e3e; }
        .btn-success { background: #2b8a3e; }
        .btn-purple { background: #5c3dc9; }
        .btn-orange { background: #e67700; }
        .btn-pink { background: #d6336c; }
        .btn-gray { background: #495057; }
        .btn-sm { padding: 6px 10px; font-size: 10px; min-height: 32px; }
        .btn:disabled { opacity: 0.4; transform: none; }

        .btn-group { display: flex; gap: 6px; flex-wrap: wrap; }
        .btn-group .btn { flex: 1; min-width: 50px; }

        .status {
            padding: 8px 12px;
            border-radius: 8px;
            margin-bottom: 10px;
            font-size: 12px;
            background: #1a1a2e;
            border: 1px solid #2a2a3e;
            text-align: center;
        }
        .status.success { color: #8ce99a; }
        .status.error { color: #ff6b6b; }
        .status.info { color: #4dabf7; }
        .status.warning { color: #ffd43b; }

        .progress-box {
            background: #1a1a2e;
            border-radius: 8px;
            padding: 10px 12px;
            margin-bottom: 10px;
            border: 1px solid #2a2a3e;
        }
        .progress-bar {
            width: 100%;
            height: 6px;
            background: #0f0f23;
            border-radius: 3px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #4dabf7, #8ce99a);
            width: 0%;
            transition: width 0.3s;
            border-radius: 3px;
        }
        .progress-info {
            display: flex;
            justify-content: space-between;
            font-size: 10px;
            color: #888;
            margin-top: 4px;
        }

        .tabs {
            display: flex;
            gap: 4px;
            margin-bottom: 10px;
            overflow-x: auto;
            padding: 2px 0;
        }
        .tab-btn {
            padding: 8px 12px;
            background: #1a1a2e;
            border: 1px solid #2a2a3e;
            border-radius: 8px;
            color: #888;
            font-size: 11px;
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.3s;
            min-height: 36px;
            flex: 1;
        }
        .tab-btn:active { transform: scale(0.95); }
        .tab-btn.active { background: #339af0; color: white; border-color: #339af0; }

        .tab-content {
            display: none;
            background: #1a1a2e;
            border-radius: 10px;
            padding: 12px;
            border: 1px solid #2a2a3e;
            max-height: 420px;
            overflow-y: auto;
        }
        .tab-content.active { display: block; }

        .results-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 8px;
            border-bottom: 1px solid #2a2a3e;
            margin-bottom: 8px;
        }
        .results-header h3 { font-size: 13px; color: #ffd43b; }
        .results-header .count { font-size: 12px; color: #8ce99a; }

        .result-item {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 4px;
            padding: 8px 0;
            border-bottom: 1px solid #0f0f23;
        }
        .result-item .name { font-size: 13px; color: #d4d4d4; min-width: 70px; font-weight: bold; }
        .result-item .country { font-size: 10px; color: #888; padding: 2px 8px; background: #0f0f23; border-radius: 10px; }
        .result-item .category { font-size: 9px; color: #cc5de8; padding: 2px 6px; background: #0f0f23; border-radius: 10px; }
        .result-item .status-badge { font-size: 9px; padding: 2px 8px; border-radius: 10px; background: #2b8a3e; color: white; }
        .result-item .url { font-size: 10px; color: #4dabf7; text-decoration: none; word-break: break-all; flex: 1; min-width: 100px; }

        .breach-item {
            padding: 8px 10px;
            margin-bottom: 6px;
            background: #0f0f23;
            border-radius: 6px;
            border-left: 3px solid #ff6b6b;
        }
        .breach-item .breach-name { color: #ff6b6b; font-weight: bold; font-size: 13px; }
        .breach-item .breach-date { color: #888; font-size: 10px; margin-left: 8px; }
        .breach-item .breach-desc { color: #aaa; font-size: 10px; margin-top: 4px; }

        .no-breaches { padding: 20px; text-align: center; color: #8ce99a; font-size: 13px; }

        .log-text {
            font-family: 'Courier New', monospace;
            font-size: 10px;
            color: #d4d4d4;
            white-space: pre-wrap;
            word-wrap: break-word;
            line-height: 1.6;
            max-height: 350px;
            overflow-y: auto;
        }
        .log-text .green { color: #8ce99a; }
        .log-text .red { color: #ff6b6b; }
        .log-text .yellow { color: #ffd43b; }
        .log-text .blue { color: #4dabf7; }
        .log-text .purple { color: #cc5de8; }
        .log-text .orange { color: #ff922b; }

        .info-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 6px;
        }
        .info-card {
            background: #0f0f23;
            padding: 10px;
            border-radius: 6px;
            text-align: center;
        }
        .info-card .label { font-size: 9px; color: #888; }
        .info-card .value { font-size: 14px; font-weight: bold; color: #d4d4d4; margin-top: 4px; }
        .info-card .value.green { color: #8ce99a; }
        .info-card .value.red { color: #ff6b6b; }
        .info-card .value.yellow { color: #ffd43b; }
        .info-card .value.blue { color: #4dabf7; }

        .footer { text-align: center; padding: 15px; font-size: 9px; color: #333; margin-top: 10px; }

        ::-webkit-scrollbar { width: 3px; height: 3px; }
        ::-webkit-scrollbar-track { background: #0f0f23; }
        ::-webkit-scrollbar-thumb { background: #2a2a3e; border-radius: 2px; }

        .spinner {
            display: inline-block;
            width: 14px;
            height: 14px;
            border: 2px solid #2a2a3e;
            border-top: 2px solid #4dabf7;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            vertical-align: middle;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .hidden { display: none !important; }

        @media (max-width: 400px) {
            .logo-text { font-size: 7px; }
            .search-row input { font-size: 13px; }
            .btn { font-size: 11px; padding: 8px 10px; }
            .result-item .name { font-size: 12px; min-width: 60px; }
        }
    </style>
</head>
<body>
<div class="container">
    <div class="logo">
        <div class="logo-text">
╔══════════════════════════════════════════╗
║  <span class="y">███████╗███╗   ██╗ ██████╗  ██████╗</span>   ║
║  <span class="y">██╔════╝████╗  ██║██╔═══██╗██╔═══██╗</span>  ║
║  <span class="g">███████╗██╔██╗ ██║██║   ██║██║   ██║</span>  ║
║  <span class="g">╚════██║██║╚██╗██║██║   ██║██║   ██║</span>  ║
║  <span class="b">███████║██║ ╚████║╚██████╔╝╚██████╔╝</span>  ║
║  <span class="b">╚══════╝╚═╝  ╚═══╝ ╚═════╝  ╚═════╝ </span>  ║
╚══════════════════════════════════════════╝
        </div>
        <div class="info-bar">
            <span class="version">v2.0 PRO</span>
            <span class="mode">| Режим: FULL OSINT</span>
            <span class="db">| База: 20 Websites</span>
            <span class="modules">| IP | Email | Phone | Gov | Graph</span>
        </div>
    </div>

    <div class="search-box">
        <div class="search-row">
            <input type="text" id="searchInput" placeholder="Введите ник, email, телефон..." />
        </div>
        <div class="btn-group">
            <button class="btn btn-primary" id="scanBtn" onclick="startFullScan()">🚀 ПОЛНЫЙ ПОИСК</button>
            <button class="btn btn-danger" id="stopBtn" onclick="stopScan()" disabled>⏹ СТОП</button>
        </div>
        <div class="btn-group" style="margin-top: 6px;">
            <button class="btn btn-success btn-sm" onclick="quickScan('ip')">🌐 IP</button>
            <button class="btn btn-orange btn-sm" onclick="quickScan('email')">📧 Email</button>
            <button class="btn btn-purple btn-sm" onclick="quickScan('phone')">📱 Phone</button>
            <button class="btn btn-gray btn-sm" onclick="clearAll()">🗑️ Очистить</button>
        </div>
    </div>

    <div class="status success" id="status">✅ Готов к работе</div>

    <div class="progress-box">
        <div class="progress-bar">
            <div class="progress-fill" id="progressFill"></div>
        </div>
        <div class="progress-info">
            <span id="progressLabel">0%</span>
            <span id="progressStats">0 / 0</span>
        </div>
    </div>

    <div class="tabs">
        <button class="tab-btn active" data-tab="results" onclick="switchTab('results')">📊 Результаты</button>
        <button class="tab-btn" data-tab="breaches" onclick="switchTab('breaches')">💀 Утечки</button>
        <button class="tab-btn" data-tab="log" onclick="switchTab('log')">📝 Лог</button>
        <button class="tab-btn" data-tab="info" onclick="switchTab('info')">ℹ️ Инфо</button>
    </div>

    <div class="tab-content active" id="tab-results">
        <div class="results-header">
            <h3>📊 РЕЗУЛЬТАТЫ ПОИСКА</h3>
            <span class="count" id="resultsCount">Найдено: 0</span>
        </div>
        <div id="resultsList">
            <div style="padding: 20px; text-align: center; color: #666; font-size: 13px;">
                🔍 Введите цель и нажмите "Поиск"
            </div>
        </div>
    </div>

    <div class="tab-content" id="tab-breaches">
        <div id="breachesList">
            <div class="no-breaches">✅ Проверка утечек будет выполнена при поиске</div>
        </div>
    </div>

    <div class="tab-content" id="tab-log">
        <div class="log-text" id="logContent">
            <span class="yellow">[+] SNOOP PRO v2.0 загружен</span><br>
            <span class="blue">[+] База: 20 Websites</span><br>
            <span class="green">[+] Готов к работе</span>
        </div>
    </div>

    <div class="tab-content" id="tab-info">
        <div class="info-grid">
            <div class="info-card">
                <div class="label">Найдено аккаунтов</div>
                <div class="value green" id="infoAccounts">0</div>
            </div>
            <div class="info-card">
                <div class="label">Найдено утечек</div>
                <div class="value red" id="infoBreaches">0</div>
            </div>
            <div class="info-card">
                <div class="label">Проверено сайтов</div>
                <div class="value blue" id="infoChecked">0</div>
            </div>
            <div class="info-card">
                <div class="label">Статус</div>
                <div class="value yellow" id="infoStatus">Готов</div>
            </div>
        </div>
        <div style="margin-top: 10px; padding: 10px; background: #0f0f23; border-radius: 6px; text-align: center; font-size: 11px; color: #666;">
            SNOOP PRO v2.0 • OSINT Intelligence Tool
        </div>
    </div>

    <div class="footer">SNOOP PRO v2.0 • OSINT Intelligence Tool</div>
</div>

<script>
// ============ СОСТОЯНИЕ ============
let isScanning = false;
let stopRequested = false;
let foundAccounts = [];
let breachResults = [];
let logLines = [
    '<span class="yellow">[+] SNOOP PRO v2.0 загружен</span>',
    '<span class="blue">[+] База: 20 Websites</span>',
    '<span class="green">[+] Готов к работе</span>'
];

// ============ ВКЛАДКИ ============
function switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.querySelector(`.tab-btn[data-tab="${tab}"]`).classList.add('active');
    document.getElementById(`tab-${tab}`).classList.add('active');
}

// ============ ЛОГ ============
function addLog(message, color = 'white') {
    const colors = {'green':'green','red':'red','yellow':'yellow','blue':'blue','purple':'purple','orange':'orange','white':''};
    const cls = colors[color] || '';
    logLines.push(`<span class="${cls}">${message}</span>`);
    document.getElementById('logContent').innerHTML = logLines.join('<br>');
    document.getElementById('logContent').scrollTop = document.getElementById('logContent').scrollHeight;
}

// ============ СТАТУС ============
function setStatus(text, type = 'success') {
    const el = document.getElementById('status');
    el.textContent = text;
    el.className = `status ${type}`;
    document.getElementById('infoStatus').textContent = text.replace(/[^a-zA-Zа-яА-Я0-9 ]/g, '');
}

// ============ ПРОГРЕСС ============
function updateProgress(current, total) {
    const pct = total > 0 ? Math.round((current / total) * 100) : 0;
    document.getElementById('progressFill').style.width = pct + '%';
    document.getElementById('progressLabel').textContent = pct + '%';
    document.getElementById('progressStats').textContent = `${current} / ${total}`;
}

// ============ ДОБАВЛЕНИЕ РЕЗУЛЬТАТА ============
function addResult(name, country, category, url) {
    foundAccounts.push({ name, country, category, url });

    const list = document.getElementById('resultsList');
    // Убираем заглушку
    if (list.querySelector('div[style]')) {
        list.innerHTML = '';
    }
    const item = document.createElement('div');
    item.className = 'result-item';
    item.innerHTML = `
        <span class="name">${name}</span>
        <span class="country">${country}</span>
        <span class="category">${category}</span>
        <span class="status-badge">✅ НАЙДЕН</span>
        <a href="${url}" target="_blank" class="url">${url}</a>
    `;
    list.appendChild(item);

    document.getElementById('resultsCount').textContent = `Найдено: ${foundAccounts.length}`;
    document.getElementById('infoAccounts').textContent = foundAccounts.length;
}

// ============ ДОБАВЛЕНИЕ УТЕЧКИ ============
function addBreach(name, date, desc) {
    breachResults.push({ name, date, desc });

    const list = document.getElementById('breachesList');
    if (list.querySelector('.no-breaches')) {
        list.innerHTML = '';
    }
    const item = document.createElement('div');
    item.className = 'breach-item';
    item.innerHTML = `
        <div>
            <span class="breach-name">🔴 ${name}</span>
            <span class="breach-date">${date}</span>
        </div>
        <div class="breach-desc">${desc}</div>
    `;
    list.appendChild(item);

    document.getElementById('infoBreaches').textContent = breachResults.length;
}

// ============ ОЧИСТКА ============
function clearAll() {
    foundAccounts = [];
    breachResults = [];
    logLines = ['<span class="yellow">[+] Все очищено</span>'];

    document.getElementById('resultsList').innerHTML = `
        <div style="padding: 20px; text-align: center; color: #666; font-size: 13px;">
            🔍 Введите цель и нажмите "Поиск"
        </div>
    `;
    document.getElementById('breachesList').innerHTML = `
        <div class="no-breaches">✅ Результаты утечек будут здесь</div>
    `;
    document.getElementById('logContent').innerHTML = logLines.join('<br>');
    document.getElementById('resultsCount').textContent = 'Найдено: 0';
    document.getElementById('infoAccounts').textContent = '0';
    document.getElementById('infoBreaches').textContent = '0';
    document.getElementById('infoChecked').textContent = '0';
    document.getElementById('progressFill').style.width = '0%';
    document.getElementById('progressLabel').textContent = '0%';
    document.getElementById('progressStats').textContent = '0 / 0';
    setStatus('✅ Готов к работе', 'success');
    addLog('[+] Все очищено', 'yellow');
}

// ============ ОСТАНОВКА ============
function stopScan() {
    stopRequested = true;
    addLog('[!] Остановка сканирования...', 'yellow');
    setStatus('⏹ Остановка...', 'warning');
}

// ============ СКАНИРОВАНИЕ ============
async function startFullScan() {
    if (isScanning) return;

    const target = document.getElementById('searchInput').value.trim();
    if (!target) {
        setStatus('❌ Введите цель для поиска!', 'error');
        return;
    }

    // Очищаем результаты
    document.getElementById('resultsList').innerHTML = '';
    document.getElementById('breachesList').innerHTML = '<div style="padding: 10px; text-align: center; color: #888;">⏳ Поиск...</div>';
    foundAccounts = [];
    breachResults = [];
    stopRequested = false;
    isScanning = true;

    document.getElementById('scanBtn').disabled = true;
    document.getElementById('scanBtn').textContent = '⏳ СКАНИРУЕТСЯ...';
    document.getElementById('stopBtn').disabled = false;

    setStatus(`🔍 Сканирование: ${target}`, 'info');
    addLog('═══════════════════════════════════════════════', 'yellow');
    addLog(`[+] ЗАПУСК ПОЛНОГО СКАНИРОВАНИЯ: ${target}`, 'purple');

    try {
        const response = await fetch('/api/scan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target })
        });

        const data = await response.json();

        if (data.accounts) {
            data.accounts.forEach(acc => {
                addResult(acc.name, acc.country, acc.category, acc.url);
            });
        }

        if (data.breaches) {
            document.getElementById('breachesList').innerHTML = '';
            data.breaches.forEach(b => {
                addBreach(b.name, b.date, b.desc);
            });
            if (data.breaches.length === 0) {
                document.getElementById('breachesList').innerHTML = `
                    <div class="no-breaches">✅ Не найден в утечках</div>
                `;
            }
        }

        if (data.logs) {
            data.logs.forEach(log => addLog(log.msg, log.color));
        }

        document.getElementById('infoChecked').textContent = data.checked || 0;

        if (stopRequested) {
            setStatus('⏹ Остановлен пользователем', 'warning');
            addLog('[!] Сканирование прервано пользователем', 'yellow');
        } else {
            setStatus(`✅ Готов | Найдено: ${foundAccounts.length}`, 'success');
            addLog(`[✓] Сканирование завершено!`, 'green');
            addLog(`[+] Найдено аккаунтов: ${foundAccounts.length}`, 'yellow');
            if (breachResults.length > 0) {
                addLog(`[+] Найдено утечек: ${breachResults.length}`, 'red');
            }
        }

    } catch (e) {
        setStatus(`❌ Ошибка: ${e.message}`, 'error');
        addLog(`[!] Ошибка: ${e.message}`, 'red');
    }

    isScanning = false;
    document.getElementById('scanBtn').disabled = false;
    document.getElementById('scanBtn').textContent = '🚀 ПОЛНЫЙ ПОИСК';
    document.getElementById('stopBtn').disabled = true;
}

// ============ БЫСТРЫЙ ПОИСК ============
function quickScan(type) {
    const target = document.getElementById('searchInput').value.trim();
    if (!target) {
        setStatus('❌ Введите цель для поиска!', 'error');
        return;
    }

    addLog(`[+] Запуск модуля ${type.toUpperCase()}: ${target}`, 'purple');
    setStatus(`🔍 ${type.toUpperCase()}: ${target}`, 'info');

    fetch('/api/quick', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target, type })
    })
    .then(r => r.json())
    .then(data => {
        if (data.logs) {
            data.logs.forEach(log => addLog(log.msg, log.color));
        }
        if (data.result) {
            addLog(`[+] Результат: ${data.result}`, 'green');
        }
        setStatus('✅ Готов', 'success');
    })
    .catch(e => {
        setStatus(`❌ Ошибка: ${e.message}`, 'error');
    });
}

// ============ ENTER ============
document.getElementById('searchInput').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') startFullScan();
});

// ============ ОБНОВЛЕНИЕ ПРОГРЕССА ============
setInterval(() => {
    fetch('/api/status')
        .then(r => r.json())
        .then(data => {
            if (data.progress) {
                updateProgress(data.progress.current, data.progress.total);
            }
        })
        .catch(() => {});
}, 2000);

// ============ ПРОВЕРКА СТАТУСА СКАНИРОВАНИЯ ============
setInterval(async () => {
    if (isScanning) {
        try {
            const resp = await fetch('/api/status');
            const data = await resp.json();
            if (data.progress) {
                updateProgress(data.progress.current, data.progress.total);
            }
        } catch(e) {}
    }
}, 1000);
</script>
</body>
</html>
"""


# ============ API ============
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/scan', methods=['POST'])
def scan():
    global stop_scan, scan_logs, scan_results
    data = request.json
    target = data.get('target', '')
    stop_scan = False
    scan_logs = []
    scan_results = []

    add_log(f"[+] Цель: {target}", 'purple')

    results = {'accounts': [], 'breaches': [], 'logs': [], 'checked': 0}

    try:
        # Определяем тип цели
        if '@' in target and '.' in target:
            # Email
            add_log(f"[+] Поиск по Email: {target}", 'blue')
            breaches = check_breaches(target)
            results['breaches'] = breaches
            if breaches:
                add_log(f"[!] Найдено утечек: {len(breaches)}", 'red')
                for b in breaches[:3]:
                    add_log(f"    • {b['name']} ({b['date']})", 'red')
            else:
                add_log("[+] Не найден в утечках", 'green')
            username = target.split('@')[0]
            accounts = scan_username(username)
            results['accounts'] = accounts
            results['checked'] = len(WEBSITES_DB)

        elif re.match(r'^\d+\.\d+\.\d+\.\d+$', target):
            # IP
            add_log(f"[+] Анализ IP: {target}", 'blue')
            try:
                hostname = socket.gethostbyaddr(target)[0]
                add_log(f"  Hostname: {hostname}", 'green')
                results['result'] = f"IP: {target} | Hostname: {hostname}"
            except:
                add_log("  Нет PTR записи", 'red')
                results['result'] = f"IP: {target} | Нет PTR записи"

        elif re.match(r'^\+?\d{10,15}$', target.replace(" ", "").replace("-", "")):
            # Phone
            add_log(f"[+] Проверка телефона: {target}", 'blue')
            try:
                import phonenumbers
                from phonenumbers import carrier, geocoder
                parsed = phonenumbers.parse(target, None)
                country = geocoder.description_for_number(parsed, "ru")
                operator = carrier.name_for_number(parsed, "ru")
                add_log(f"  Страна: {country}", 'green')
                add_log(f"  Оператор: {operator}", 'green')
                results['result'] = f"Страна: {country} | Оператор: {operator}"
            except Exception as e:
                add_log(f"  Ошибка: {str(e)}", 'red')
                results['result'] = "Ошибка парсинга номера"

        else:
            # Username
            add_log(f"[+] Поиск по никнейму: {target}", 'blue')
            accounts = scan_username(target)
            results['accounts'] = accounts
            results['checked'] = len(WEBSITES_DB)

            # Проверяем утечки
            for domain in ['gmail.com', 'yandex.ru', 'mail.ru']:
                email = f"{target}@{domain}"
                breaches = check_breaches(email)
                if breaches:
                    results['breaches'] = breaches
                    add_log(f"[!] Найдены утечки для {email}", 'red')
                    for b in breaches[:3]:
                        add_log(f"    • {b['name']} ({b['date']})", 'red')
                    break
            if not results.get('breaches'):
                add_log("[+] Не найден в утечках", 'green')

    except Exception as e:
        add_log(f"[!] Ошибка: {str(e)}", 'red')

    results['logs'] = scan_logs
    return jsonify(results)


@app.route('/api/quick', methods=['POST'])
def quick_scan():
    data = request.json
    target = data.get('target', '')
    scan_type = data.get('type', '')

    logs = []
    result = ""

    if scan_type == 'ip':
        logs.append({'msg': f"[+] Анализ IP: {target}", 'color': 'blue'})
        try:
            hostname = socket.gethostbyaddr(target)[0]
            logs.append({'msg': f"  Hostname: {hostname}", 'color': 'green'})
            result = f"IP: {target} | Hostname: {hostname}"
        except:
            logs.append({'msg': "  Нет PTR записи", 'color': 'red'})
            result = f"IP: {target} | Нет PTR записи"

    elif scan_type == 'email':
        logs.append({'msg': f"[+] Проверка Email: {target}", 'color': 'blue'})
        breaches = check_breaches(target)
        if breaches:
            logs.append({'msg': f"[!] Найдено утечек: {len(breaches)}", 'color': 'red'})
            for b in breaches[:3]:
                logs.append({'msg': f"  • {b['name']} ({b['date']})", 'color': 'red'})
            result = f"Найдено утечек: {len(breaches)}"
        else:
            logs.append({'msg': "  ✅ Не найден в утечках", 'color': 'green'})
            result = "Не найден в утечках"

    elif scan_type == 'phone':
        logs.append({'msg': f"[+] Проверка телефона: {target}", 'color': 'blue'})
        try:
            import phonenumbers
            from phonenumbers import carrier, geocoder
            parsed = phonenumbers.parse(target, None)
            country = geocoder.description_for_number(parsed, "ru")
            operator = carrier.name_for_number(parsed, "ru")
            logs.append({'msg': f"  Страна: {country}", 'color': 'green'})
            logs.append({'msg': f"  Оператор: {operator}", 'color': 'green'})
            result = f"Страна: {country} | Оператор: {operator}"
        except:
            logs.append({'msg': "  Ошибка парсинга номера", 'color': 'red'})
            result = "Ошибка парсинга номера"

    return jsonify({'logs': logs, 'result': result})


@app.route('/api/status')
def status():
    return jsonify({'progress': {'current': len(scan_results), 'total': len(WEBSITES_DB)}})


if __name__ == '__main__':
    import socket
    import os


    def get_local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"


    local_ip = get_local_ip()

    print("""
╔═══════════════════════════════════════════════════════════╗
║  ███████╗███╗   ██╗ ██████╗  ██████╗ ██████╗   ██████╗  ║
║  ██╔════╝████╗  ██║██╔═══██╗██╔═══██╗██╔══██╗ ██╔═══██╗ ║
║  ███████╗██╔██╗ ██║██║   ██║██║   ██║██████╔╝ ██║   ██║ ║
║  ╚════██║██║╚██╗██║██║   ██║██║   ██║██╔═══╝  ██║   ██║ ║
║  ███████║██║ ╚████║╚██████╔╝╚██████╔╝██║      ╚██████╔╝ ║
║  ╚══════╝╚═╝  ╚═══╝ ╚═════╝  ╚═════╝ ╚═╝       ╚═════╝  ║
╚═══════════════════════════════════════════════════════════╝
    """)
    print("  SNOOP PRO v2.0 Mobile OSINT Tool")
    print("  ==================================")
    print(f"  📱 Откройте на телефоне: http://{local_ip}:5000")
    print(f"  🔍 Для локального доступа: http://127.0.0.1:5000")
    print("  ==================================")
    print("  ⚠️ Для доступа с телефона:")
    print("  1. Телефон и компьютер в одной Wi-Fi сети")
    print("  2. Откройте браузер на телефоне")
    print(f"  3. Введите: http://{local_ip}:5000")
    print("  ==================================\n")

    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)