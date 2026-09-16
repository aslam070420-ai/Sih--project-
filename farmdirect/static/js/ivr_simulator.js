/* ============================================================
   FarmDirect IVR Simulator — cinematic multilingual client
   - Same backend APIs as real phone calls
   - English + all 22 Scheduled Indian languages
   - Browser TTS/STT uses each language's registered India locale
   - DTMF, speech and text remain the existing interaction channels
   ============================================================ */
(function () {
  const S = window.IVR_SCRIPT_ROOT || '';
  const LANGS = Array.isArray(window.IVR_LANGUAGES) ? window.IVR_LANGUAGES : [];
  const LANG_META = Object.fromEntries(LANGS.map(item => [item.code, item]));
  const $ = (id) => document.getElementById(id);

  let sessionToken = null;
  let callActive = false;
  let callStartTs = null;
  let timerHandle = null;
  let currentLang = ($('ivr-language-select') && $('ivr-language-select').value) || 'ta';
  let recognition = null;
  let recognizing = false;
  let lastRecognizedText = '';
  let microphoneGranted = false;
  let recognitionSeq = 0;
  let currentMenu = 'idle';
  let dtmfBuffer = '';
  let dtmfBusy = false;

  function log(...args) { console.log('[IVR]', ...args); }
  function metaFor(code) { return LANG_META[code] || LANG_META.en || { code: 'en', native: 'English', english: 'English', locale: 'en-IN', dtmf: '02' }; }
  function localeFor(code) { return metaFor(code).locale || 'en-IN'; }
  function nameFor(code) {
    const m = metaFor(code);
    return m.native === m.english ? m.native : `${m.native} · ${m.english}`;
  }
  function micHint() { return `Tap to speak · ${nameFor(currentLang)}`; }

  function setSttStatus(kind, message) {
    const el = $('ivr-stt-status');
    if (!el) return;
    el.classList.remove('is-ready', 'is-listening', 'is-error');
    if (kind) el.classList.add(`is-${kind}`);
    const icon = kind === 'error' ? 'bi-exclamation-triangle' : (kind === 'listening' ? 'bi-soundwave' : 'bi-mic');
    el.innerHTML = `<i class="bi ${icon}"></i> ${escapeHtml(message)}`;
  }

  function refreshSttLocale() {
    if ($('ivr-stt-locale')) $('ivr-stt-locale').textContent = localeFor(currentLang);
  }

  // ---------------- TTS via browser SpeechSynthesis ----------------
  function speak(text, lang) {
    if (!('speechSynthesis' in window) || !text) return;
    try {
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      const want = localeFor(lang);
      u.lang = want;
      u.rate = 0.95;
      u.pitch = 1;
      const voices = window.speechSynthesis.getVoices() || [];
      const exact = voices.find(v => (v.lang || '').toLowerCase() === want.toLowerCase());
      const base = want.split('-')[0].toLowerCase();
      const match = exact || voices.find(v => (v.lang || '').toLowerCase().startsWith(base));
      if (match) u.voice = match;
      const phone = document.querySelector('.ivr-phone');
      u.onstart = () => phone && phone.classList.add('is-speaking');
      u.onend = u.onerror = () => phone && phone.classList.remove('is-speaking');
      window.speechSynthesis.speak(u);
    } catch (e) { log('TTS error', e); }
  }

  // ---------------- STT via browser SpeechRecognition ----------------
  async function ensureMicrophonePermission() {
    if (microphoneGranted) return true;
    if (!window.isSecureContext && !['localhost', '127.0.0.1'].includes(location.hostname)) {
      throw new Error('Microphone access needs HTTPS or localhost.');
    }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      // Some Chrome builds let SpeechRecognition request permission directly.
      return true;
    }
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    stream.getTracks().forEach(track => track.stop());
    microphoneGranted = true;
    return true;
  }

  function initRecognition() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return null;
    const r = new SR();
    const mySeq = ++recognitionSeq;
    let hadRecognitionError = false;
    r.continuous = false;
    r.interimResults = true;
    r.maxAlternatives = 3;
    r.lang = localeFor(currentLang);
    r.onstart = () => {
      if (mySeq !== recognitionSeq) return;
      recognizing = true;
      $('ivr-mic-btn').classList.add('recording');
      document.querySelector('.ivr-phone')?.classList.add('is-listening');
      $('ivr-mic-hint').textContent = `Listening · ${nameFor(currentLang)}…`;
      setSttStatus('listening', `Listening in ${metaFor(currentLang).english}`);
    };
    r.onend = () => {
      if (mySeq !== recognitionSeq) return;
      recognizing = false;
      $('ivr-mic-btn').classList.remove('recording');
      document.querySelector('.ivr-phone')?.classList.remove('is-listening');
      if (!hadRecognitionError) $('ivr-mic-hint').textContent = micHint();
      if (lastRecognizedText) {
        $('ivr-mic-result').textContent = lastRecognizedText;
        $('ivr-send-voice').disabled = false;
        if (!hadRecognitionError) setSttStatus('ready', 'Transcript ready');
      } else if (!hadRecognitionError) {
        setSttStatus('ready', `Voice-to-text ready · ${localeFor(currentLang)}`);
      }
      recognition = null;
    };
    r.onresult = (ev) => {
      if (mySeq !== recognitionSeq) return;
      let finalText = '';
      let interimText = '';
      for (let i = 0; i < ev.results.length; i += 1) {
        const chunk = (ev.results[i][0]?.transcript || '').trim();
        if (!chunk) continue;
        if (ev.results[i].isFinal) finalText += (finalText ? ' ' : '') + chunk;
        else interimText += (interimText ? ' ' : '') + chunk;
      }
      const combined = `${finalText}${finalText && interimText ? ' ' : ''}${interimText}`.trim();
      if (combined) lastRecognizedText = combined;
      $('ivr-mic-result').textContent = combined || lastRecognizedText;
      $('ivr-send-voice').disabled = !(finalText || lastRecognizedText);
    };
    r.onnomatch = () => {
      if (mySeq !== recognitionSeq) return;
      hadRecognitionError = true;
      $('ivr-mic-hint').textContent = `No clear speech detected · tap to retry in ${nameFor(currentLang)}`;
      setSttStatus('error', 'No speech match · retry');
    };
    r.onerror = (e) => {
      if (mySeq !== recognitionSeq) return;
      hadRecognitionError = true;
      log('STT error', e.error);
      recognizing = false;
      $('ivr-mic-btn').classList.remove('recording');
      document.querySelector('.ivr-phone')?.classList.remove('is-listening');
      const messages = {
        'not-allowed': 'Microphone permission blocked · allow mic for this site',
        'service-not-allowed': 'Chrome speech service is blocked on this device',
        'audio-capture': 'No working microphone was found',
        'no-speech': `No speech heard · tap and speak in ${metaFor(currentLang).english}`,
        'network': 'Speech recognition needs network access in this browser',
        'language-not-supported': `Browser STT does not expose ${localeFor(currentLang)} · use Text fallback`,
        'aborted': 'Voice recognition stopped',
      };
      const msg = messages[e.error] || `Voice-to-text error: ${e.error || 'unknown'}`;
      $('ivr-mic-hint').textContent = msg;
      setSttStatus(e.error === 'aborted' ? 'ready' : 'error', msg);
      recognition = null;
    };
    return r;
  }

  async function startRecognition() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      const msg = 'Voice-to-text is not supported by this browser. Use Chrome/Edge or Text input.';
      $('ivr-mic-hint').textContent = msg;
      setSttStatus('error', 'SpeechRecognition unavailable');
      return;
    }
    if (recognizing && recognition) {
      try { recognition.stop(); } catch (_) {}
      return;
    }
    try {
      // Prevent IVR TTS from being transcribed as caller speech.
      window.speechSynthesis?.cancel();
      await ensureMicrophonePermission();
      lastRecognizedText = '';
      $('ivr-mic-result').textContent = '';
      $('ivr-send-voice').disabled = true;
      if (recognition) { try { recognition.abort(); } catch (_) {} }
      recognition = initRecognition();
      if (!recognition) return;
      recognition.lang = localeFor(currentLang);
      refreshSttLocale();
      setSttStatus('ready', `Starting ${localeFor(currentLang)}…`);
      // A short gap after cancelling speech synthesis avoids Android Chrome
      // treating the IVR's final TTS audio as microphone input.
      await new Promise(resolve => setTimeout(resolve, 160));
      recognition.start();
    } catch (e) {
      log('Mic permission/start error', e);
      const msg = (e && (e.name === 'NotAllowedError' || e.name === 'PermissionDeniedError'))
        ? 'Microphone permission denied · enable Microphone for Chrome and this site'
        : (e.message || 'Unable to start voice-to-text');
      $('ivr-mic-hint').textContent = msg;
      setSttStatus('error', msg);
      recognizing = false;
      recognition = null;
    }
  }

  // ---------------- API helpers ----------------
  async function apiPost(url, body) {
    const res = await fetch(S + url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}),
    });
    const json = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(json.error || 'Request failed');
    return json;
  }

  // ---------------- transcript rendering ----------------
  function escapeHtml(value) {
    return String(value || '').replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[m]);
  }
  function addBubble(role, text, intent) {
    const wrap = $('ivr-transcript');
    wrap.querySelector('.ivr-empty')?.remove();
    const div = document.createElement('div');
    div.className = `ivr-bubble ${role === 'user' ? 'user' : 'system'}`;
    if (role === 'user') {
      div.innerHTML = `<span class="ivr-bubble-tag">YOU</span>${escapeHtml(text)}` +
        (intent ? ` <span class="ivr-bubble-intent">${escapeHtml(intent)}</span>` : '');
    } else {
      div.innerHTML = `<span class="ivr-bubble-tag">IVR · ${escapeHtml(metaFor(currentLang).native || '')}</span>${escapeHtml(text)}`;
    }
    wrap.appendChild(div);
    wrap.scrollTop = wrap.scrollHeight;
  }

  // ---------------- call lifecycle ----------------
  async function startCall() {
    const caller = currentCaller();
    if (!caller) { alert('Please pick a caller number first.'); return false; }
    currentLang = ($('ivr-language-select') && $('ivr-language-select').value) || currentLang;
    addBubble('system', `Connecting · ${nameFor(currentLang)}…`);
    try {
      const r = await apiPost('/api/ivr/incoming', {
        caller_number: caller,
        language: currentLang,
        source: 'simulator',
      });
      sessionToken = r.session_token;
      callActive = true;
      callStartTs = Date.now();
      currentLang = r.language || currentLang;
      setUILang(currentLang, false);
      updateModePill(r.mode);
      renderPrompts(r.prompt || []);
      updateState(r);
      startTimer();
      showCallUI();
      return true;
    } catch (e) {
      addBubble('system', 'Error: ' + e.message);
      return false;
    }
  }

  async function hangup() {
    if (sessionToken) {
      try { await apiPost('/api/ivr/hangup', { session_token: sessionToken }); }
      catch (e) { log('hangup err', e); }
    }
    stopCallUI();
  }

  function stopCallUI() {
    callActive = false;
    stopTimer();
    window.speechSynthesis?.cancel();
    document.querySelector('.ivr-phone')?.classList.remove('is-call-active', 'is-speaking', 'is-listening');
    $('ivr-call-btn').style.display = '';
    $('ivr-hangup-btn').style.display = 'none';
    $('ivr-input-tabs').style.display = 'none';
    $('ivr-keypad').style.display = 'none';
    $('ivr-voice-input').style.display = 'none';
    $('ivr-text-input').style.display = 'none';
    $('ivr-actions').style.display = 'none';
    $('ivr-call-state').textContent = 'Call ended';
    currentMenu = 'idle';
    resetDtmfBuffer();
    sessionToken = null;
  }

  function showCallUI() {
    document.querySelector('.ivr-phone')?.classList.add('is-call-active');
    $('ivr-call-btn').style.display = 'none';
    $('ivr-hangup-btn').style.display = '';
    $('ivr-input-tabs').style.display = 'flex';
    $('ivr-keypad').style.display = 'grid';
    $('ivr-actions').style.display = 'flex';
    $('ivr-call-state').textContent = `Connected · ${metaFor(currentLang).native}`;
    $('ivr-state-card').style.display = '';
    $('ivr-intent-card').style.display = '';
    setUILang(currentLang, false);
  }

  function startTimer() {
    stopTimer();
    timerHandle = setInterval(() => {
      const sec = Math.floor((Date.now() - callStartTs) / 1000);
      $('ivr-timer').textContent = `${String(Math.floor(sec / 60)).padStart(2, '0')}:${String(sec % 60).padStart(2, '0')}`;
    }, 500);
  }
  function stopTimer() { if (timerHandle) clearInterval(timerHandle); timerHandle = null; }

  // ---------------- input & language ----------------
  function renderDtmfBuffer(message) {
    const el = $('ivr-dtmf-buffer');
    if (!el) return;
    if (currentMenu === 'language_select') {
      el.style.display = '';
      el.textContent = message || `Language code: ${dtmfBuffer || '__'}`;
    } else {
      el.style.display = 'none';
      el.textContent = '';
    }
  }

  function resetDtmfBuffer() {
    dtmfBuffer = '';
    dtmfBusy = false;
    renderDtmfBuffer();
  }

  async function handleKeypadDigit(digit) {
    if (!callActive || dtmfBusy) return;
    // Language selection is the only menu that requires a multi-digit code.
    // Buffer the two digits locally so 15 is sent as "15", not "1" then "5".
    if (currentMenu === 'language_select') {
      if (digit === '*') {
        dtmfBuffer = '';
        renderDtmfBuffer('Language code cleared · enter 01–23');
        return;
      }
      if (digit === '#') {
        if (dtmfBuffer.length !== 2) {
          renderDtmfBuffer(`Enter both digits · ${dtmfBuffer || '__'}`);
          return;
        }
      } else if (/^\d$/.test(digit)) {
        if (dtmfBuffer.length >= 2) dtmfBuffer = '';
        dtmfBuffer += digit;
        renderDtmfBuffer(`Language code: ${dtmfBuffer.padEnd(2, '_')}`);
        if (dtmfBuffer.length < 2) return;
      } else {
        return;
      }

      const code = dtmfBuffer;
      dtmfBusy = true;
      renderDtmfBuffer(`Selecting language ${code}…`);
      try {
        await sendInput({ dtmf: code });
      } finally {
        dtmfBuffer = '';
        dtmfBusy = false;
        renderDtmfBuffer();
      }
      return;
    }
    await sendInput({ dtmf: digit });
  }

  async function sendInput({ text, dtmf }) {
    if (!sessionToken) return null;
    try {
      const r = await apiPost('/api/ivr/input', {
        session_token: sessionToken,
        input: text || null,
        dtmf: dtmf || null,
        caller_number: currentCaller(),
        source: 'simulator',
      });
      if (text) addBubble('user', text, r.intent || '');
      if (dtmf) addBubble('user', 'DTMF ' + dtmf, r.intent || '');
      if (r.language) setUILang(r.language, false);
      renderPrompts(r.prompt || []);
      updateState(r);
      updateIntent(r);
      updateAction(r.action);
      updateModePill(r.mode);
      if (r.ended) { addBubble('system', 'Call ended by IVR.'); stopCallUI(); }
      return r;
    } catch (e) {
      addBubble('system', 'Error: ' + e.message);
      return null;
    }
  }

  async function switchCallLanguage(lang, announce = true) {
    if (!LANG_META[lang]) return false;
    setUILang(lang, false);
    if (!callActive || !sessionToken) return true;
    try {
      const r = await apiPost('/api/ivr/language', { session_token: sessionToken, language: lang });
      currentLang = r.language || lang;
      setUILang(currentLang, false);
      if (announce) addBubble('user', `Language → ${nameFor(currentLang)}`, 'LANGUAGE_CHANGE');
      renderPrompts(r.prompt || []);
      updateState(r);
      updateModePill(r.mode);
      return true;
    } catch (e) {
      addBubble('system', 'Language switch error: ' + e.message);
      return false;
    }
  }

  function renderPrompts(prompts) {
    if (!prompts || !prompts.length) return;
    const text = prompts.filter(Boolean).join(' ');
    addBubble('system', text);
    speak(text, currentLang);
  }

  // ---------------- UI updates ----------------
  function updateState(r) {
    if (r.language) currentLang = r.language;
    const nextMenu = r.current_menu || currentMenu || '—';
    if (nextMenu !== currentMenu) {
      currentMenu = nextMenu;
      dtmfBuffer = '';
      dtmfBusy = false;
      renderDtmfBuffer();
    }
    $('ivr-session-token').textContent = r.session_token ? r.session_token.slice(0, 12) + '…' : '—';
    $('ivr-session-lang').textContent = r.language ? nameFor(r.language) : '—';
    $('ivr-session-menu').textContent = currentMenu || '—';
    $('ivr-session-auth').textContent = r.auth_status || '—';
    $('ivr-session-farmer').textContent = r.farmer_name ||
      ((window.IVR_FARMERS || []).find(f => f.phone === currentCaller()) || {}).name || '—';
    $('ivr-session-fails').textContent = String(r.failure_count || 0);
    $('ivr-contact-num').textContent = currentCaller() ? ('+91 ' + String(currentCaller()).slice(-10)) : '—';
    if (callActive) $('ivr-call-state').textContent = `Connected · ${metaFor(currentLang).native}`;
  }

  function updateIntent(r) {
    $('ivr-intent-name').textContent = r.intent || '—';
    const conf = (r.intent_payload && r.intent_payload.confidence) || 0;
    $('ivr-intent-conf').textContent = `${Math.round(conf * 100)}%`;
    $('ivr-intent-json').textContent = JSON.stringify(r.intent_payload || {}, null, 2);
  }

  function updateAction(action) {
    if (!action) { $('ivr-action-card').style.display = 'none'; return; }
    $('ivr-action-card').style.display = '';
    $('ivr-action-name').textContent = action.name || '—';
    $('ivr-action-json').textContent = JSON.stringify(action.result || action.error || {}, null, 2);
  }

  function updateModePill(mode) {
    if (!mode) return;
    const pill = $('ivr-mode-pill');
    pill.textContent = (mode.mode || 'mock').toUpperCase();
    pill.style.background = mode.mode === 'production' ? '#fdeaea' : 'var(--fd-amber-light)';
    pill.style.color = mode.mode === 'production' ? '#b03a2e' : '#9a6b06';
    $('ivr-provider').textContent = `${(mode.mode || 'sim').toUpperCase()} · ${mode.telephony || 'MOCK'}`;
  }

  function currentCaller() {
    const checked = document.querySelector('input[name="caller_number"]:checked');
    if (checked && checked.value) return checked.value;
    return $('ivr-custom-caller').value.trim() || '';
  }

  function setUILang(lang, updateServer = false) {
    if (!LANG_META[lang]) lang = 'en';
    const changed = currentLang !== lang;
    if (changed && recognition) {
      recognitionSeq += 1;
      try { recognition.abort(); } catch (_) {}
      recognition = null;
      recognizing = false;
      $('ivr-mic-btn')?.classList.remove('recording');
      document.querySelector('.ivr-phone')?.classList.remove('is-listening');
    }
    currentLang = lang;
    if ($('ivr-language-select')) $('ivr-language-select').value = lang;
    if ($('ivr-lang-code')) $('ivr-lang-code').textContent = metaFor(lang).dtmf || '--';
    if ($('ivr-mic-hint') && !recognizing) $('ivr-mic-hint').textContent = micHint();
    refreshSttLocale();
    if (!recognizing) setSttStatus('ready', `Voice-to-text ready · ${localeFor(lang)}`);
    if ($('ivr-text-field')) $('ivr-text-field').placeholder = `Type in ${metaFor(lang).english} and press Enter`;
    if ($('ivr-session-lang') && callActive) $('ivr-session-lang').textContent = nameFor(lang);
    if (updateServer && callActive) switchCallLanguage(lang);
  }

  // ---------------- wire events ----------------
  function wire() {
    setUILang(currentLang, false);
    if (!('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)) {
      setSttStatus('error', 'SpeechRecognition unavailable in this browser');
    }
    $('ivr-call-btn').addEventListener('click', startCall);
    $('ivr-hangup-btn').addEventListener('click', hangup);

    $('ivr-language-select').addEventListener('change', (e) => setUILang(e.target.value, true));

    document.querySelectorAll('.ivr-input-tabs button').forEach(b => {
      b.addEventListener('click', () => {
        document.querySelectorAll('.ivr-input-tabs button').forEach(x => x.classList.remove('active'));
        b.classList.add('active');
        const mode = b.dataset.mode;
        $('ivr-keypad').style.display = mode === 'keypad' ? 'grid' : 'none';
        $('ivr-voice-input').style.display = mode === 'voice' ? 'flex' : 'none';
        $('ivr-text-input').style.display = mode === 'text' ? 'flex' : 'none';
      });
    });

    document.querySelectorAll('.ivr-key').forEach(k => {
      k.addEventListener('click', () => {
        k.classList.remove('key-hit'); void k.offsetWidth; k.classList.add('key-hit');
        if (callActive) handleKeypadDigit(k.dataset.d);
      });
    });

    $('ivr-mic-btn').addEventListener('click', startRecognition);

    $('ivr-send-voice').addEventListener('click', () => {
      if (!lastRecognizedText) return;
      sendInput({ text: lastRecognizedText });
      lastRecognizedText = '';
      $('ivr-mic-result').textContent = '';
      $('ivr-send-voice').disabled = true;
    });

    $('ivr-text-field').addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && e.target.value.trim()) {
        sendInput({ text: e.target.value.trim() });
        e.target.value = '';
      }
    });
    $('ivr-send-text').addEventListener('click', () => {
      const v = $('ivr-text-field').value.trim();
      if (!v) return;
      sendInput({ text: v });
      $('ivr-text-field').value = '';
    });

    $('ivr-repeat').addEventListener('click', () => sendInput({ text: currentLang === 'ta' ? 'மீண்டும் சொல்லுங்கள்' : 'repeat' }));
    $('ivr-back').addEventListener('click', () => sendInput({ text: currentLang === 'ta' ? 'பின்னாடி போ' : 'go back' }));
    $('ivr-main').addEventListener('click', () => sendInput({ text: currentLang === 'ta' ? 'முக்கிய மெனு' : 'main menu' }));

    $('ivr-use-custom').addEventListener('click', () => {
      const v = $('ivr-custom-caller').value.trim();
      if (!v) return;
      document.querySelectorAll('.ivr-caller-radio').forEach(r => { r.checked = false; });
      $('ivr-contact-num').textContent = v;
    });

    document.querySelectorAll('.ivr-script-btn').forEach(btn => btn.addEventListener('click', () => runScript(btn.dataset.script)));
  }

  // ---------------- scripted demos ----------------
  async function runScript(name) {
    const scriptLang = name.includes('tamil') || name.includes('price_tamil') || name.includes('order_tamil') || name.includes('earn_tamil') ? 'ta' : 'en';
    setUILang(scriptLang, false);
    if (!callActive) {
      const first = document.querySelector('input[name="caller_number"]');
      if (first) first.checked = true;
      const started = await startCall();
      if (!started) return;
      await new Promise(r => setTimeout(r, 700));
    } else {
      await switchCallLanguage(scriptLang, false);
      await new Promise(r => setTimeout(r, 450));
    }

    const scripts = {
      list_tamil: [
        { text: 'என்னிடம் 100 கிலோ தக்காளி இருக்கு' }, { text: '38' }, { text: 'இன்று' }, { dtmf: '2' }, { dtmf: '1' },
      ],
      list_en: [
        { text: 'I have 200 kilos of onion' }, { text: '19' }, { text: 'today' }, { dtmf: '2' }, { dtmf: '1' },
      ],
      price_tamil: [{ text: 'இன்று தக்காளி விலை என்ன?' }],
      order_tamil: [{ text: 'என்னுடைய ஆர்டர் எங்கே?' }],
      bulk_en: [{ text: 'Are there any bulk orders?' }, { dtmf: '1' }],
      earn_tamil: [{ text: 'எனக்கு எவ்வளவு பணம் வந்திருக்கு?' }],
      more_en: [{ dtmf: '9' }, { dtmf: '2' }],
      place_order_en: [{ text: 'place order' }, { text: 'tomato' }, { text: '2 kg' }, { dtmf: '1' }, { dtmf: '1' }],
    };
    for (const step of (scripts[name] || [])) {
      await sendInput(step);
      await new Promise(r => setTimeout(r, 1000));
    }
  }

  if (document.readyState !== 'loading') wire();
  else document.addEventListener('DOMContentLoaded', wire);

  if ('speechSynthesis' in window) {
    window.speechSynthesis.onvoiceschanged = () => {};
    window.speechSynthesis.getVoices();
  }
})();
