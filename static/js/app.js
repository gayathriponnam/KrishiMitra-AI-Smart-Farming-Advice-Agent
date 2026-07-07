/* ============================================================================
   KrishiMitra — app.js  |  Full Frontend Logic
   Chat, Dashboard, Weather, Market Prices, Profiles, Reports, Voice I/O
   ============================================================================ */

// ── State ─────────────────────────────────────────────────────────────────────
const App = {
  currentTab:      'chat',
  currentLanguage: localStorage.getItem('km_language') || 'en',
  darkMode:        localStorage.getItem('km_dark') === 'true',
  ttsEnabled:      localStorage.getItem('km_tts') === 'true',
  currentProfile:  null,
  config:          {},
  isRecording:     false,
  recognition:     null,
  synth:           window.speechSynthesis || null,
};

// ── Initialization ─────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  initDarkMode();
  initVoice();
  initTextAreaAutoResize();
  initCharCounter();

  await loadConfig();
  loadProfiles();
  fetchMarketPrices();

  // Auto-load dashboard data
  loadWeatherDashboard();
  loadMarketDashboard();
  buildFarmingCalendar();

  // Set language from storage
  document.getElementById('languageSelect').value = App.currentLanguage;
  document.getElementById('languageSelect').addEventListener('change', (e) => {
    App.currentLanguage = e.target.value;
    localStorage.setItem('km_language', App.currentLanguage);
  });

  // Enter key to send
  document.getElementById('chatInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // TTS toggle
  document.getElementById('ttsToggle').addEventListener('click', () => {
    App.ttsEnabled = !App.ttsEnabled;
    localStorage.setItem('km_tts', App.ttsEnabled);
    document.getElementById('ttsToggle').classList.toggle('active', App.ttsEnabled);
    showToast(App.ttsEnabled ? 'Voice responses enabled' : 'Voice responses disabled', 'KrishiMitra');
  });
  document.getElementById('ttsToggle').classList.toggle('active', App.ttsEnabled);
});

// ── Config ─────────────────────────────────────────────────────────────────────
async function loadConfig() {
  try {
    const res = await fetch('/api/config');
    if (res.ok) {
      App.config = await res.json();
      updateStatusBadge(App.config.watsonx_available);
      if (App.config.current_season) {
        document.getElementById('seasonText').textContent =
          App.config.current_season.split('—')[0].trim();
      }
    }
  } catch (e) {
    updateStatusBadge(false);
  }
}

function updateStatusBadge(watsonxConnected) {
  const badge = document.getElementById('statusBadge');
  const text = document.getElementById('statusText');
  badge.className = 'badge status-badge ' + (watsonxConnected ? 'connected' : 'demo');
  text.textContent = watsonxConnected ? 'IBM Granite' : 'Demo Mode';
}

// ── Dark Mode ──────────────────────────────────────────────────────────────────
function initDarkMode() {
  if (App.darkMode) applyDarkMode(true, false);

  document.getElementById('darkModeToggle').addEventListener('click', () => {
    App.darkMode = !App.darkMode;
    localStorage.setItem('km_dark', App.darkMode);
    applyDarkMode(App.darkMode, true);
  });
}

function applyDarkMode(enable, animate) {
  document.documentElement.setAttribute('data-bs-theme', enable ? 'dark' : 'light');
  const icon = document.getElementById('darkModeIcon');
  icon.className = enable ? 'bi bi-sun-fill' : 'bi bi-moon-stars-fill';
  if (animate) document.body.style.transition = 'background .3s, color .3s';
}

// ── Tab Switching ──────────────────────────────────────────────────────────────
function switchTab(tabId) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.sidebar-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.mobile-nav-btn').forEach(b => b.classList.remove('active'));

  const panel = document.getElementById(`panel-${tabId}`);
  if (panel) panel.classList.add('active');

  const sidebarBtn = document.getElementById(`sidebar${capitalize(tabId)}`);
  if (sidebarBtn) sidebarBtn.classList.add('active');

  // Mobile nav match
  const mobileMap = { chat:0, dashboard:1, weather:2, market:3, profile:4 };
  const mobileIdx = mobileMap[tabId];
  if (mobileIdx !== undefined) {
    document.querySelectorAll('.mobile-nav-btn')[mobileIdx]?.classList.add('active');
  }

  App.currentTab = tabId;

  // Lazy-load panel data
  if (tabId === 'market')    fetchMarketPrices();
  if (tabId === 'weather')   tryAutoWeather();
  if (tabId === 'dashboard') { loadWeatherDashboard(); loadMarketDashboard(); }
  if (tabId === 'profile')   loadProfiles();
  if (tabId === 'reports')   loadReportsList();
}

function capitalize(str) {
  const map = {
    'chat': 'Chat', 'dashboard': 'Dashboard', 'crop-recommendation': 'CropRec',
    'weather': 'Weather', 'soil': 'Soil', 'pest': 'Pest',
    'irrigation': 'Irrigation', 'market': 'Market',
    'profile': 'Profile', 'reports': 'Reports'
  };
  return map[str] || (str.charAt(0).toUpperCase() + str.slice(1));
}

function tryAutoWeather() {
  const loc = document.getElementById('locationInput').value.trim();
  if (loc && loc !== 'India') {
    document.getElementById('weatherLocation').value = loc;
    fetchWeather();
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// CHAT FUNCTIONS
// ══════════════════════════════════════════════════════════════════════════════

async function sendMessage() {
  const input = document.getElementById('chatInput');
  const message = input.value.trim();
  if (!message) return;

  const sendBtn = document.getElementById('sendBtn');
  sendBtn.disabled = true;
  input.value = '';
  autoResizeTextarea(input);
  document.getElementById('charCount').textContent = '0/2000';

  // Hide quick prompts after first message
  document.getElementById('quickPrompts').style.display = 'none';

  appendMessage('user', message);
  showTypingIndicator(true);
  scrollChatToBottom();

  const location = document.getElementById('locationInput').value.trim() || 'India';
  const profileId = App.currentProfile?.profile_id;

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        language: App.currentLanguage,
        location,
        profile_id: profileId,
      }),
    });

    showTypingIndicator(false);

    if (res.ok) {
      const data = await res.json();
      appendMessage('assistant', data.response);
      if (App.ttsEnabled) speakText(data.response);
    } else {
      const err = await res.json();
      appendMessage('assistant', `⚠️ ${err.error || 'Sorry, something went wrong. Please try again.'}`);
    }
  } catch (e) {
    showTypingIndicator(false);
    appendMessage('assistant', '⚠️ Connection error. Please check your internet connection and try again.');
  }

  sendBtn.disabled = false;
  input.focus();
  scrollChatToBottom();
}

function sendQuickMessage(text) {
  document.getElementById('chatInput').value = text;
  autoResizeTextarea(document.getElementById('chatInput'));
  sendMessage();
}

function appendMessage(role, content) {
  const container = document.getElementById('chatMessages');
  const isUser = role === 'user';

  const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const formattedContent = formatMessageContent(content);

  const msgEl = document.createElement('div');
  msgEl.className = `chat-message ${role} fade-in-up`;
  msgEl.innerHTML = `
    <div class="message-avatar ${isUser ? 'user' : 'assistant'}-avatar">
      ${isUser ? '👨‍🌾' : '🌾'}
    </div>
    <div class="message-content">
      <div class="message-bubble ${isUser ? 'user' : 'assistant'}-bubble">
        ${isUser ? '' : `<div class="message-header"><strong>KrishiMitra</strong><span class="message-time">${time}</span></div>`}
        <div class="message-text">${formattedContent}</div>
        ${isUser ? '' : `
          <div class="message-actions mt-2">
            <button class="toolbar-btn" onclick="speakText(this)" data-text="${escapeAttr(content)}" title="Read aloud">
              <i class="bi bi-volume-up"></i>
            </button>
            <button class="toolbar-btn" onclick="copyText(this)" data-text="${escapeAttr(content)}" title="Copy">
              <i class="bi bi-clipboard"></i>
            </button>
          </div>
        `}
      </div>
    </div>`;

  container.appendChild(msgEl);
  scrollChatToBottom();
}

function formatMessageContent(text) {
  if (!text) return '';
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/^### (.*$)/gm, '<h4>$1</h4>')
    .replace(/^## (.*$)/gm, '<h3>$1</h3>')
    .replace(/^# (.*$)/gm, '<h2>$1</h2>')
    .replace(/^\- (.*$)/gm, '<li>$1</li>')
    .replace(/^(\d+)\. (.*$)/gm, '<li>$2</li>')
    .replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>');
}

function escapeAttr(text) {
  return text.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function copyText(btn) {
  const text = btn.getAttribute('data-text');
  navigator.clipboard.writeText(text).then(() => {
    const original = btn.innerHTML;
    btn.innerHTML = '<i class="bi bi-check2"></i>';
    setTimeout(() => btn.innerHTML = original, 1500);
  });
}

function showTypingIndicator(show) {
  document.getElementById('typingIndicator').classList.toggle('d-none', !show);
  if (show) scrollChatToBottom();
}

function scrollChatToBottom() {
  const container = document.getElementById('chatMessages');
  setTimeout(() => container.scrollTop = container.scrollHeight, 50);
}

async function clearChat() {
  if (!confirm('Clear all chat messages?')) return;
  document.getElementById('chatMessages').innerHTML = '';
  document.getElementById('quickPrompts').style.display = '';
  await fetch('/api/chat/clear', { method: 'POST' });
  showToast('Chat cleared', 'KrishiMitra');
}

function downloadChat() {
  const messages = document.querySelectorAll('.chat-message');
  let text = 'KrishiMitra — Farming Advisory Chat Export\n';
  text += '=' .repeat(50) + '\n\n';
  messages.forEach(msg => {
    const role = msg.classList.contains('user') ? 'Farmer' : 'KrishiMitra';
    const content = msg.querySelector('.message-text')?.innerText || '';
    text += `${role}:\n${content}\n\n${'-'.repeat(40)}\n\n`;
  });

  const blob = new Blob([text], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `krishimitra_chat_${new Date().toISOString().slice(0,10)}.txt`;
  a.click();
  URL.revokeObjectURL(url);
}

// ── TextArea ───────────────────────────────────────────────────────────────────
function initTextAreaAutoResize() {
  const ta = document.getElementById('chatInput');
  ta.addEventListener('input', () => autoResizeTextarea(ta));
}

function autoResizeTextarea(ta) {
  ta.style.height = 'auto';
  ta.style.height = Math.min(ta.scrollHeight, 140) + 'px';
}

function initCharCounter() {
  document.getElementById('chatInput').addEventListener('input', (e) => {
    document.getElementById('charCount').textContent = `${e.target.value.length}/2000`;
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// VOICE I/O
// ══════════════════════════════════════════════════════════════════════════════

function initVoice() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const voiceBtn = document.getElementById('voiceBtn');

  if (!SpeechRecognition) {
    voiceBtn.title = 'Voice input not supported in this browser';
    voiceBtn.style.opacity = '.5';
    voiceBtn.onclick = () => showToast('Voice input requires Chrome or Edge browser', '🎤');
    return;
  }

  App.recognition = new SpeechRecognition();
  App.recognition.continuous = false;
  App.recognition.interimResults = false;

  App.recognition.onstart = () => {
    App.isRecording = true;
    voiceBtn.classList.add('recording');
    voiceBtn.innerHTML = '<i class="bi bi-stop-circle-fill"></i>';
    voiceBtn.title = 'Recording... Click to stop';
  };

  App.recognition.onresult = (e) => {
    const transcript = e.results[0][0].transcript;
    document.getElementById('chatInput').value = transcript;
    autoResizeTextarea(document.getElementById('chatInput'));
    document.getElementById('charCount').textContent = `${transcript.length}/2000`;
    stopRecording();
    sendMessage();
  };

  App.recognition.onerror = (e) => {
    stopRecording();
    if (e.error !== 'no-speech') showToast(`Voice error: ${e.error}`, '🎤');
  };

  App.recognition.onend = () => stopRecording();

  voiceBtn.addEventListener('click', () => {
    if (App.isRecording) {
      App.recognition.stop();
    } else {
      const lang = App.currentLanguage;
      const langCodes = {
        en:'en-IN', hi:'hi-IN', te:'te-IN', ta:'ta-IN',
        kn:'kn-IN', mr:'mr-IN', gu:'gu-IN', pa:'pa-IN', bn:'bn-IN'
      };
      App.recognition.lang = langCodes[lang] || 'en-IN';
      App.recognition.start();
    }
  });
}

function stopRecording() {
  App.isRecording = false;
  const voiceBtn = document.getElementById('voiceBtn');
  voiceBtn.classList.remove('recording');
  voiceBtn.innerHTML = '<i class="bi bi-mic-fill"></i>';
  voiceBtn.title = 'Voice Input (Speech-to-Text)';
}

function speakText(btnOrText) {
  if (!App.synth) return;
  App.synth.cancel();

  let text = typeof btnOrText === 'string' ? btnOrText
           : btnOrText.getAttribute('data-text');

  // Strip markdown formatting
  text = text.replace(/\*\*(.*?)\*\*/g, '$1')
             .replace(/\*(.*?)\*/g, '$1')
             .replace(/`([^`]+)`/g, '$1')
             .replace(/<[^>]+>/g, '')
             .replace(/[#>*]/g, '')
             .substring(0, 800);  // limit length

  const utterance = new SpeechSynthesisUtterance(text);

  // Select language voice
  const langVoiceMap = { hi: 'hi-IN', te: 'te-IN', ta: 'ta-IN', kn: 'kn-IN' };
  utterance.lang = langVoiceMap[App.currentLanguage] || 'en-IN';
  utterance.rate = 0.9;
  utterance.pitch = 1.0;

  App.synth.speak(utterance);
}

// ══════════════════════════════════════════════════════════════════════════════
// WEATHER
// ══════════════════════════════════════════════════════════════════════════════

async function fetchWeather() {
  const location = document.getElementById('weatherLocation').value.trim() ||
                   document.getElementById('locationInput').value.trim();
  if (!location) { showToast('Please enter a location', 'Weather'); return; }

  document.getElementById('weatherDisplay').innerHTML = loadingHTML('Fetching weather data...');

  try {
    const res = await fetch(`/api/weather?location=${encodeURIComponent(location)}`);
    const data = await res.json();
    renderWeather(data, 'weatherDisplay');
  } catch (e) {
    document.getElementById('weatherDisplay').innerHTML = errorHTML('Failed to fetch weather data.');
  }
}

function renderWeather(data, containerId) {
  const container = document.getElementById(containerId);
  const forecastHTML = (data.forecast || []).map(f => `
    <div class="col">
      <div class="forecast-card">
        <div class="fw-bold small">${f.date}</div>
        <div class="my-1">${getWeatherEmoji(f.description)}</div>
        <div class="forecast-temp">${f.temp_max}° / ${f.temp_min}°</div>
        <div class="text-muted" style="font-size:.73rem">${f.description}</div>
        <div class="text-muted" style="font-size:.73rem">💧 ${f.humidity}%</div>
      </div>
    </div>
  `).join('');

  const advisoryHTML = (data.advisory || []).map(a =>
    `<div class="advisory-item">${a}</div>`
  ).join('');

  const alertHTML = (data.alerts || []).map(a =>
    `<div class="alert alert-warning py-2 small mb-2"><i class="bi bi-exclamation-triangle me-2"></i>${a}</div>`
  ).join('');

  container.innerHTML = `
    ${alertHTML}
    <div class="weather-main-card">
      <div class="row align-items-center">
        <div class="col-8">
          <div class="weather-temp">${data.temperature}°C</div>
          <div class="weather-desc">${getWeatherEmoji(data.description)} ${data.description}</div>
          <div class="weather-detail mt-2">
            📍 ${data.location} &nbsp;|&nbsp;
            💧 ${data.humidity}% &nbsp;|&nbsp;
            💨 ${data.wind_speed} km/h
          </div>
          <div class="weather-detail">🌡️ Feels like ${data.feels_like}°C</div>
        </div>
        <div class="col-4 text-end">
          <div style="font-size:4rem;opacity:.9">${getWeatherEmoji(data.description)}</div>
          <div style="font-size:.8rem;opacity:.8">${data.season?.split('—')[0] || ''}</div>
        </div>
      </div>
    </div>

    ${data.forecast?.length ? `
      <h6 class="mb-3 text-muted"><i class="bi bi-calendar3 me-2"></i>5-Day Forecast</h6>
      <div class="row row-cols-2 row-cols-sm-3 row-cols-md-5 g-2 mb-3">
        ${forecastHTML}
      </div>
    ` : ''}

    ${advisoryHTML ? `
      <h6 class="mb-2 text-muted"><i class="bi bi-info-circle me-2"></i>Agricultural Advisory</h6>
      ${advisoryHTML}
    ` : ''}

    <div class="text-muted small mt-2">
      <i class="bi bi-cloud-download me-1"></i>Source: ${data.source}
    </div>
  `;
}

function getWeatherEmoji(desc) {
  if (!desc) return '🌤️';
  const d = desc.toLowerCase();
  if (d.includes('thunderstorm')) return '⛈️';
  if (d.includes('rain') || d.includes('drizzle')) return '🌧️';
  if (d.includes('snow')) return '❄️';
  if (d.includes('cloud')) return '⛅';
  if (d.includes('fog') || d.includes('mist') || d.includes('haze')) return '🌫️';
  if (d.includes('clear') || d.includes('sunny')) return '☀️';
  return '🌤️';
}

async function loadWeatherDashboard() {
  const location = document.getElementById('locationInput').value.trim() || 'Delhi';
  document.getElementById('dashWeatherBody').innerHTML = loadingHTML('');
  try {
    const res = await fetch(`/api/weather?location=${encodeURIComponent(location)}`);
    const data = await res.json();
    document.getElementById('dashTemp').textContent = `${data.temperature}°C`;
    document.getElementById('dashHumidity').textContent = `${data.humidity}%`;

    const advisoryHTML = (data.advisory || []).slice(0, 3).map(a =>
      `<div class="advisory-item small">${a}</div>`
    ).join('');

    document.getElementById('dashWeatherBody').innerHTML = `
      <div class="d-flex align-items-center mb-3">
        <div style="font-size:2.5rem;margin-right:14px">${getWeatherEmoji(data.description)}</div>
        <div>
          <div class="fw-bold">${data.temperature}°C — ${data.description}</div>
          <div class="text-muted small">📍 ${data.location} | 💧 ${data.humidity}% | 💨 ${data.wind_speed} km/h</div>
        </div>
      </div>
      ${advisoryHTML}
    `;
  } catch {
    document.getElementById('dashWeatherBody').innerHTML = errorHTML('Weather unavailable');
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// MARKET PRICES
// ══════════════════════════════════════════════════════════════════════════════

async function fetchMarketPrices() {
  const crop = document.getElementById('marketCropFilter')?.value?.trim() || '';
  const location = document.getElementById('marketLocationFilter')?.value?.trim() || '';
  const display = document.getElementById('marketPricesDisplay');
  if (display) display.innerHTML = loadingHTML('Fetching market prices...');

  try {
    const params = new URLSearchParams();
    if (crop) params.set('crop', crop);
    if (location) params.set('location', location);

    const res = await fetch(`/api/market-prices?${params}`);
    const data = await res.json();
    renderMarketPrices(data);
  } catch (e) {
    if (display) display.innerHTML = errorHTML('Failed to fetch market prices.');
  }
}

function renderMarketPrices(data) {
  const display = document.getElementById('marketPricesDisplay');
  if (!display) return;

  const priceRows = (data.prices || []).map(p => `
    <tr>
      <td><strong>${p.crop}</strong></td>
      <td class="text-muted">${p.market}</td>
      <td>₹${p.min_price?.toLocaleString()}</td>
      <td>₹${p.max_price?.toLocaleString()}</td>
      <td><strong>₹${p.modal_price?.toLocaleString()}</strong></td>
      <td>
        <span class="${p.vs_msp?.startsWith('↑') ? 'price-above-msp' : p.vs_msp?.startsWith('↓') ? 'price-below-msp' : ''}">
          ${p.vs_msp || '—'}
        </span>
      </td>
    </tr>
  `).join('');

  const mspRows = data.msp_rates ? Object.entries(data.msp_rates).slice(0, 8).map(([crop, msp]) =>
    `<span class="crop-badge me-1 mb-1">${crop}: ₹${msp}</span>`
  ).join('') : '';

  display.innerHTML = `
    ${mspRows ? `
      <div class="mb-3">
        <strong class="small text-muted"><i class="bi bi-award me-1"></i>MSP Rates 2024-25:</strong><br>
        <div class="mt-1">${mspRows}</div>
      </div>
    ` : ''}

    <div class="table-responsive">
      <table class="price-table">
        <thead>
          <tr>
            <th>Crop</th><th>Market</th>
            <th>Min (₹)</th><th>Max (₹)</th><th>Modal (₹)</th>
            <th>vs MSP</th>
          </tr>
        </thead>
        <tbody>${priceRows}</tbody>
      </table>
    </div>
    <div class="text-muted small mt-2">
      <i class="bi bi-info-circle me-1"></i>${data.source || ''} | Updated: ${data.last_updated || ''}
    </div>
    ${data.note ? `<div class="text-muted small mt-1"><i class="bi bi-exclamation-circle me-1"></i>${data.note}</div>` : ''}
  `;
}

async function loadMarketDashboard() {
  document.getElementById('dashMarketBody').innerHTML = loadingHTML('');
  try {
    const res = await fetch('/api/market-prices');
    const data = await res.json();
    const topPrices = (data.prices || []).slice(0, 5).map(p => `
      <div class="d-flex justify-content-between small mb-1">
        <span>${p.crop}</span>
        <span class="fw-bold text-success">₹${p.modal_price?.toLocaleString()}</span>
      </div>
    `).join('');

    document.getElementById('dashMarketBody').innerHTML = topPrices ||
      '<p class="text-muted small">No price data available</p>';
  } catch {
    document.getElementById('dashMarketBody').innerHTML = errorHTML('Market data unavailable');
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// CROP RECOMMENDATIONS
// ══════════════════════════════════════════════════════════════════════════════

async function getCropRecommendations() {
  const output = document.getElementById('cropRecommendationOutput');
  output.innerHTML = loadingHTML('Generating AI crop recommendations...');

  const payload = {
    soil_type:    document.getElementById('cropSoilType').value,
    location:     document.getElementById('cropLocation').value || 'India',
    area_acres:   parseFloat(document.getElementById('cropArea').value) || 2,
    irrigation:   document.getElementById('cropIrrigation').value,
    farming_type: document.getElementById('cropFarmingType').value,
  };

  try {
    const res = await fetch('/api/crop-recommendation', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    output.innerHTML = `
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h6 class="mb-0 text-success"><i class="bi bi-stars me-2"></i>AI Crop Recommendations</h6>
        <span class="badge bg-success">${data.season?.split('—')[0] || ''}</span>
      </div>
      <div class="ai-response-text">${formatMessageContent(data.recommendations)}</div>
      <div class="text-muted small mt-3">
        <i class="bi bi-clock me-1"></i>Generated: ${new Date(data.timestamp).toLocaleString()}
      </div>
    `;
  } catch (e) {
    output.innerHTML = errorHTML('Failed to get recommendations. Please try again.');
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// SOIL HEALTH ANALYSIS
// ══════════════════════════════════════════════════════════════════════════════

async function analyzeSoil() {
  const output = document.getElementById('soilAnalysisOutput');
  const ph = parseFloat(document.getElementById('soilPH').value);
  const oc = parseFloat(document.getElementById('soilOC').value);
  const n  = parseFloat(document.getElementById('soilN').value);
  const p  = parseFloat(document.getElementById('soilP').value);
  const k  = parseFloat(document.getElementById('soilK').value);
  const zn = parseFloat(document.getElementById('soilZn').value);
  const crop = document.getElementById('soilCropTarget').value || 'general crop';

  if (!ph && !n && !p) {
    showToast('Please enter at least pH and N/P/K values', 'Soil Analysis');
    return;
  }

  output.innerHTML = loadingHTML('Analyzing soil and generating recommendations...');

  const prompt = `My soil test results are: pH=${ph||'N/A'}, Organic Carbon=${oc||'N/A'}%, Nitrogen=${n||'N/A'} kg/ha, Phosphorus=${p||'N/A'} kg/ha, Potassium=${k||'N/A'} kg/ha, Zinc=${zn||'N/A'} ppm. I plan to grow ${crop}. Please interpret these values, identify deficiencies, and give complete fertilizer and soil amendment recommendations including specific products, doses per acre, and application timing.`;

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: prompt, language: App.currentLanguage }),
    });
    const data = await res.json();

    // Also render visual indicators
    const indicators = renderSoilIndicators({ ph, oc, n, p, k, zn });

    output.innerHTML = `
      <h6 class="text-success mb-3"><i class="bi bi-search-heart me-2"></i>Soil Analysis Report</h6>
      ${indicators}
      <hr>
      <div class="ai-response-text">${formatMessageContent(data.response)}</div>
    `;
  } catch (e) {
    output.innerHTML = errorHTML('Analysis failed. Please try again.');
  }
}

function renderSoilIndicators(vals) {
  const items = [
    { label: 'pH Level', value: vals.ph, unit: '', min: 3, max: 10, ideal_min: 6, ideal_max: 7.5 },
    { label: 'Organic Carbon', value: vals.oc, unit: '%', min: 0, max: 2, ideal_min: 0.5, ideal_max: 0.75 },
    { label: 'Nitrogen (N)', value: vals.n, unit: 'kg/ha', min: 0, max: 600, ideal_min: 280, ideal_max: 600 },
    { label: 'Phosphorus (P)', value: vals.p, unit: 'kg/ha', min: 0, max: 60, ideal_min: 20, ideal_max: 60 },
    { label: 'Potassium (K)', value: vals.k, unit: 'kg/ha', min: 0, max: 600, ideal_min: 200, ideal_max: 600 },
    { label: 'Zinc (Zn)', value: vals.zn, unit: 'ppm', min: 0, max: 3, ideal_min: 0.8, ideal_max: 3 },
  ];

  return items.filter(i => !isNaN(i.value) && i.value !== undefined).map(item => {
    const pct = Math.min(100, Math.max(0, ((item.value - item.min) / (item.max - item.min)) * 100));
    const status = item.value < item.ideal_min ? 'low' : item.value > item.ideal_max ? 'high' : 'medium';
    const statusText = { low: '⬇️ Low', medium: '✅ Adequate', high: '⬆️ High' }[status];

    return `
      <div class="soil-indicator">
        <div class="soil-indicator-label">
          <span><strong>${item.label}</strong>: ${item.value} ${item.unit}</span>
          <span class="text-${status === 'low' ? 'danger' : status === 'medium' ? 'success' : 'warning'}">${statusText}</span>
        </div>
        <div class="soil-bar">
          <div class="soil-bar-fill ${status}" style="width:${pct}%"></div>
        </div>
      </div>`;
  }).join('');
}

// ══════════════════════════════════════════════════════════════════════════════
// PEST & DISEASE DIAGNOSIS
// ══════════════════════════════════════════════════════════════════════════════

async function diagnosePest() {
  const output = document.getElementById('pestDiagnosisOutput');
  const crop = document.getElementById('pestCrop').value;
  const part = document.getElementById('pestPlantPart').value;
  const symptoms = document.getElementById('pestSymptoms').value;
  const spread = document.getElementById('pestSpread').value;

  if (!crop || !symptoms) {
    showToast('Please enter the crop name and describe the symptoms', 'Pest Advisory');
    return;
  }

  output.innerHTML = loadingHTML('Diagnosing crop problem using AI...');

  const prompt = `My ${crop} crop has a problem. Affected part: ${part}. Approximately ${spread}% of plants are affected. Symptoms: ${symptoms}. Please identify the likely pest or disease, provide severity assessment, and give complete IPM treatment recommendations including organic options first, then chemical if needed. Include dosage, application method, safety precautions, and when to consult a local expert.`;

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: prompt, language: App.currentLanguage }),
    });
    const data = await res.json();
    output.innerHTML = `
      <div class="d-flex align-items-center mb-3 gap-2">
        <h6 class="mb-0 text-danger"><i class="bi bi-bug-fill me-2"></i>AI Diagnosis & Treatment</h6>
        <span class="badge ${parseInt(spread) > 50 ? 'bg-danger' : parseInt(spread) > 20 ? 'bg-warning' : 'bg-success'}">
          ${parseInt(spread) > 50 ? 'Severe' : parseInt(spread) > 20 ? 'Moderate' : 'Mild'} (${spread}% affected)
        </span>
      </div>
      <div class="ai-response-text">${formatMessageContent(data.response)}</div>
    `;
  } catch (e) {
    output.innerHTML = errorHTML('Diagnosis failed. Please try again.');
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// IRRIGATION PLANNER
// ══════════════════════════════════════════════════════════════════════════════

async function getIrrigationPlan() {
  const output = document.getElementById('irrigationOutput');
  const crop = document.getElementById('irrCrop').value;
  const stage = document.getElementById('irrGrowthStage').value;
  const method = document.getElementById('irrMethod').value;
  const soil = document.getElementById('irrSoilType').value;

  if (!crop) {
    showToast('Please enter the crop name', 'Irrigation');
    return;
  }

  output.innerHTML = loadingHTML('Generating irrigation plan...');

  const location = document.getElementById('locationInput').value.trim() || 'India';
  const prompt = `Create a detailed irrigation plan for ${crop} crop at ${stage} stage. Current method: ${method}. Soil type: ${soil}. Location: ${location}. Include: 1) Irrigation frequency and timing, 2) Water quantity per irrigation, 3) Critical growth stages not to miss, 4) Water-saving tips specific to this crop, 5) Signs of over/under irrigation, 6) Whether upgrading to drip would be beneficial.`;

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: prompt, language: App.currentLanguage }),
    });
    const data = await res.json();
    output.innerHTML = `
      <h6 class="text-primary mb-3"><i class="bi bi-droplet-fill me-2"></i>Irrigation Plan for ${crop}</h6>
      <div class="ai-response-text">${formatMessageContent(data.response)}</div>
    `;
  } catch (e) {
    output.innerHTML = errorHTML('Failed to generate plan. Please try again.');
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// FARM PROFILES
// ══════════════════════════════════════════════════════════════════════════════

async function loadProfiles() {
  try {
    const res = await fetch('/api/profiles');
    const data = await res.json();
    renderProfilesList(data.profiles || []);
    populateReportProfileSelect(data.profiles || []);
  } catch (e) {
    console.error('Failed to load profiles:', e);
  }
}

function renderProfilesList(profiles) {
  const container = document.getElementById('profilesList');
  if (!profiles.length) {
    container.innerHTML = `<div class="text-center text-muted py-4">
      <i class="bi bi-person-plus fs-3 d-block mb-2"></i>
      No profiles yet. Create your first farm profile!
    </div>`;
    return;
  }

  container.innerHTML = profiles.map(p => `
    <div class="profile-card slide-in ${App.currentProfile?.profile_id === p.profile_id ? 'active-profile' : ''}">
      <div class="d-flex justify-content-between align-items-start">
        <div>
          <div class="profile-card-name">🏡 ${p.farm_name || 'Unnamed Farm'}</div>
          <div class="profile-card-meta">👨‍🌾 ${p.farmer_name || 'N/A'}</div>
          <div class="profile-card-meta">📍 ${[p.village, p.district, p.state].filter(Boolean).join(', ') || 'Location not set'}</div>
          <div class="profile-card-meta">🌾 ${p.area_acres || '?'} acres | ${p.soil_type || 'Unknown soil'} | ${p.irrigation_type || 'Unknown irrigation'}</div>
        </div>
      </div>
      ${p.current_crops?.length ? `
        <div class="profile-card-crops mt-2">
          ${p.current_crops.slice(0, 5).map(c => `<span class="crop-badge">${c}</span>`).join('')}
          ${p.current_crops.length > 5 ? `<span class="crop-badge">+${p.current_crops.length - 5}</span>` : ''}
        </div>` : ''}
      <div class="d-flex gap-2 mt-2">
        <button class="btn btn-sm btn-outline-success" onclick="setActiveProfile('${p.profile_id}')">
          <i class="bi bi-check-circle me-1"></i>Set Active
        </button>
        <button class="btn btn-sm btn-outline-secondary" onclick="editProfile(${JSON.stringify(p).replace(/"/g,'&quot;')})">
          <i class="bi bi-pencil me-1"></i>Edit
        </button>
        <button class="btn btn-sm btn-outline-danger" onclick="deleteProfile('${p.profile_id}')">
          <i class="bi bi-trash3"></i>
        </button>
      </div>
    </div>
  `).join('');
}

async function saveProfile() {
  const crops = Array.from(document.getElementById('profileCrops').selectedOptions).map(o => o.value);

  const profileData = {
    profile_id:     document.getElementById('profileId').value || undefined,
    farmer_name:    document.getElementById('profileFarmerName').value,
    farm_name:      document.getElementById('profileFarmName').value,
    village:        document.getElementById('profileVillage').value,
    district:       document.getElementById('profileDistrict').value,
    state:          document.getElementById('profileState').value,
    area_acres:     parseFloat(document.getElementById('profileArea').value) || 0,
    experience_years: parseInt(document.getElementById('profileExperience').value) || 0,
    soil_type:      document.getElementById('profileSoilType').value,
    irrigation_type:document.getElementById('profileIrrigation').value,
    farming_type:   document.getElementById('profileFarmingType').value,
    current_crops:  crops,
    preferred_language: document.getElementById('profileLanguage').value,
  };

  if (!profileData.farmer_name) {
    showToast('Please enter the farmer name', 'Profile');
    return;
  }

  try {
    const res = await fetch('/api/profiles', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profileData),
    });
    const data = await res.json();
    showToast('Farm profile saved!', '✅');
    clearProfileForm();
    loadProfiles();
    setActiveProfile(data.profile.profile_id);
  } catch (e) {
    showToast('Failed to save profile', '❌');
  }
}

function editProfile(profile) {
  document.getElementById('profileId').value = profile.profile_id || '';
  document.getElementById('profileFarmerName').value = profile.farmer_name || '';
  document.getElementById('profileFarmName').value = profile.farm_name || '';
  document.getElementById('profileVillage').value = profile.village || '';
  document.getElementById('profileDistrict').value = profile.district || '';
  document.getElementById('profileState').value = profile.state || '';
  document.getElementById('profileArea').value = profile.area_acres || '';
  document.getElementById('profileExperience').value = profile.experience_years || '';
  document.getElementById('profileSoilType').value = profile.soil_type || 'Loamy';
  document.getElementById('profileIrrigation').value = profile.irrigation_type || 'Rainfed';
  document.getElementById('profileFarmingType').value = profile.farming_type || 'Conventional';
  document.getElementById('profileLanguage').value = profile.preferred_language || 'en';

  // Set multi-select crops
  const cropSelect = document.getElementById('profileCrops');
  Array.from(cropSelect.options).forEach(opt => {
    opt.selected = (profile.current_crops || []).includes(opt.value);
  });

  document.getElementById('profileFarmerName').scrollIntoView({ behavior: 'smooth' });
}

function clearProfileForm() {
  ['profileId','profileFarmerName','profileFarmName','profileVillage',
   'profileDistrict','profileArea','profileExperience'].forEach(id => {
    document.getElementById(id).value = '';
  });
  document.getElementById('profileState').value = '';
  document.getElementById('profileSoilType').value = 'Loamy';
  document.getElementById('profileIrrigation').value = 'Rainfed';
  Array.from(document.getElementById('profileCrops').options).forEach(o => o.selected = false);
}

async function deleteProfile(profileId) {
  if (!confirm('Delete this farm profile?')) return;
  await fetch(`/api/profiles/${profileId}`, { method: 'DELETE' });
  if (App.currentProfile?.profile_id === profileId) {
    App.currentProfile = null;
    updateSidebarProfile(null);
  }
  loadProfiles();
  showToast('Profile deleted', '🗑️');
}

async function setActiveProfile(profileId) {
  try {
    const res = await fetch(`/api/profiles/${profileId}`);
    App.currentProfile = await res.json();
    updateSidebarProfile(App.currentProfile);
    App.currentLanguage = App.currentProfile.preferred_language || 'en';
    document.getElementById('languageSelect').value = App.currentLanguage;
    if (App.currentProfile.village || App.currentProfile.district) {
      const loc = [App.currentProfile.village, App.currentProfile.district, App.currentProfile.state]
        .filter(Boolean).join(', ');
      document.getElementById('locationInput').value = loc;
    }
    loadProfiles();
    showToast(`Active profile: ${App.currentProfile.farm_name}`, '🏡');
  } catch (e) { console.error(e); }
}

function updateSidebarProfile(profile) {
  const nameEl = document.getElementById('profileMiniName');
  const detailEl = document.getElementById('profileMiniDetail');
  if (profile) {
    nameEl.textContent = profile.farm_name || profile.farmer_name || 'My Farm';
    detailEl.textContent = `${profile.area_acres || '?'} acres | ${profile.soil_type || ''}`;
    document.getElementById('dashCrops').textContent = profile.current_crops?.length || '--';
  } else {
    nameEl.textContent = 'No profile set';
    detailEl.textContent = 'Set up your farm profile';
  }
}

function populateReportProfileSelect(profiles) {
  const sel = document.getElementById('reportProfileSelect');
  if (!sel) return;
  sel.innerHTML = '<option value="">-- Select Profile --</option>' +
    profiles.map(p => `<option value="${p.profile_id}">${p.farm_name} (${p.farmer_name})</option>`).join('');
}

// ══════════════════════════════════════════════════════════════════════════════
// REPORTS
// ══════════════════════════════════════════════════════════════════════════════

async function generateReport() {
  const profileId = document.getElementById('reportProfileSelect').value;
  if (!profileId) {
    showToast('Please select a farm profile to generate a report', 'Reports');
    return;
  }

  document.getElementById('reportsList').innerHTML = loadingHTML('Generating farming report...');

  try {
    const res = await fetch('/api/reports/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile_id: profileId }),
    });
    const data = await res.json();

    if (data.pdf_path || data.json_path) {
      showToast('Report generated! Click download below.', '📄');
      loadReportsList();

      // Trigger auto-download
      if (data.filename) {
        const a = document.createElement('a');
        a.href = `/api/reports/download/${data.filename}`;
        a.download = `${data.filename}.pdf`;
        a.click();
      }
    } else {
      showToast(data.error || 'Report generation failed', '❌');
    }
  } catch (e) {
    showToast('Failed to generate report', '❌');
  }
}

async function loadReportsList() {
  const container = document.getElementById('reportsList');
  try {
    const res = await fetch('/api/reports/list');
    const data = await res.json();
    const reports = data.reports || [];

    if (!reports.length) {
      container.innerHTML = `<div class="text-center text-muted py-4">
        <i class="bi bi-file-earmark-text fs-3 d-block mb-2"></i>
        No reports generated yet.
      </div>`;
      return;
    }

    container.innerHTML = reports.map(r => `
      <div class="report-card slide-in">
        <div class="report-icon">${r.pdf_file ? '📄' : '📋'}</div>
        <div class="report-info">
          <div class="report-title">${r.filename}</div>
          <div class="report-meta">Generated: ${new Date(r.generated_at).toLocaleString()}</div>
          <div class="report-meta">
            ${r.pdf_file ? '<span class="badge bg-danger me-1">PDF</span>' : ''}
            ${r.json_file ? '<span class="badge bg-secondary">JSON</span>' : ''}
          </div>
        </div>
        <div class="d-flex flex-column gap-1">
          <a href="/api/reports/download/${r.filename}" class="btn btn-sm btn-success" download>
            <i class="bi bi-download me-1"></i>Download
          </a>
        </div>
      </div>
    `).join('');
  } catch (e) {
    container.innerHTML = errorHTML('Failed to load reports');
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// FARMING CALENDAR (Dashboard)
// ══════════════════════════════════════════════════════════════════════════════

function buildFarmingCalendar() {
  const calendarData = [
    { month: 'Jun', crops: ['Rice (transplant)', 'Cotton (sow)', 'Soybean'] },
    { month: 'Jul', crops: ['Rice (weeding)', 'Maize (knee-high)', 'Groundnut'] },
    { month: 'Aug', crops: ['Kharif maintenance', 'Pest scouting', 'Fertilize'] },
    { month: 'Sep', crops: ['Kharif harvest prep', 'Rabi land prep', 'FYM apply'] },
    { month: 'Oct', crops: ['Wheat (sow)', 'Mustard (sow)', 'Chickpea (sow)'] },
    { month: 'Nov', crops: ['Wheat (irrigate)', 'Rabi growing', 'Potato (plant)'] },
    { month: 'Dec', crops: ['Rabi maintenance', 'Wheat tillering', 'Onion (rabi)'] },
    { month: 'Jan', crops: ['Wheat (jointing)', 'Mustard (flower)', 'Harvest prep'] },
    { month: 'Feb', crops: ['Wheat (heading)', 'Rabi harvest', 'Summer land prep'] },
    { month: 'Mar', crops: ['Wheat harvest', 'Zaid sowing', 'Summer vegies'] },
    { month: 'Apr', crops: ['Summer crops', 'Deep plowing', 'Kharif prep'] },
    { month: 'May', crops: ['Seed procurement', 'Soil testing', 'Kharif planning'] },
  ];

  const currentMonth = new Date().toLocaleString('en', { month: 'short' });
  const container = document.getElementById('farmingCalendar');
  container.innerHTML = calendarData.map(m => `
    <div class="calendar-month ${m.month === currentMonth ? 'border-success border-2' : ''}">
      <div class="calendar-month-header ${m.month === currentMonth ? 'bg-success' : ''}">
        ${m.month} ${m.month === currentMonth ? '← Now' : ''}
      </div>
      <div class="calendar-month-body">
        ${m.crops.map(c => `<span class="calendar-crop">${c}</span>`).join('')}
      </div>
    </div>
  `).join('');
}

// ══════════════════════════════════════════════════════════════════════════════
// UTILITIES
// ══════════════════════════════════════════════════════════════════════════════

function loadingHTML(msg) {
  return `<div class="text-center py-4">
    <div class="spinner-border text-success mb-2"></div>
    ${msg ? `<p class="text-muted small">${msg}</p>` : ''}
  </div>`;
}

function errorHTML(msg) {
  return `<div class="alert alert-warning d-flex align-items-center gap-2 mt-2">
    <i class="bi bi-exclamation-triangle"></i>
    <span>${msg}</span>
  </div>`;
}

function showToast(message, title = 'KrishiMitra') {
  document.getElementById('toastTitle').textContent = title;
  document.getElementById('toastBody').textContent = message;
  const toastEl = document.getElementById('appToast');
  const toast = new bootstrap.Toast(toastEl, { delay: 3500 });
  toast.show();
}
