import functools
import http.server
import json
import base64
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import tempfile
import threading
import time
import urllib.request
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
SOURCE = (ROOT / 'code/danish_practice_tool.html').read_text(encoding='utf-8')
TEST = r'''
<script>
window.addEventListener('error', e => { window.runtimeErrors = [...(window.runtimeErrors || []), e.message]; });
setTimeout(async () => {
 const checks = [];
 function check(name, condition) { checks.push({name, passed: !!condition}); }
 try {
  check('all UI references exist', Object.values(ui).every(Boolean));
  check('split vocabulary loaded', vocabulary.verbs.length > 1);
  check('hidden answer sections take no space', getComputedStyle(ui.choiceList).display === 'none' && getComputedStyle(ui.tableGrid).display === 'none');
  ui.category.value = 'verbs'; ui.mode.value = 'forms'; ui.count.value = 2;
  ui.startBtn.click();
  check('Start button creates session', state.exercises.length === 2);
  buildSession(['verb-en-da-infinitive']);
  check('revision hidden before answering', ui.revisionPanel.hidden);
  check('reverse prompt hides Danish text and audio', !ui.promptWord.querySelector('[data-speak]') && ui.promptWord.textContent === currentExercise().record.english);
  ui.answerInput.value = currentExercise().answers[0]; ui.submitBtn.click();
  check('correct text answer scores once', state.score === 1 && state.answered && !ui.revisionPanel.hidden);
  submitAnswer(); check('repeat submission cannot increase score', state.score === 1);
  check('session separates attempts from total', ui.statScore.textContent === '1 / 1' && ui.sessionQuestion.textContent === '1 / 2');
  ui.nextBtn.click(); check('next clears revision', ui.revisionPanel.hidden && !ui.answerInput.disabled);
  ui.answerInput.value = 'deliberately incorrect'; ui.submitBtn.click();
  check('incorrect answer has feedback', state.score === 1 && ui.feedback.classList.contains('bad'));
  ui.nextBtn.click(); check('completion hides answer controls', state.complete && ui.answerRow.hidden && ui.choiceList.hidden && ui.tableGrid.hidden && ui.sessionProgress.value === 100);
  buildSessionFromPack('verb-tables');
  check('table check button visible and enabled', !ui.tableSubmitBtn.hidden && !ui.tableSubmitBtn.disabled && ui.answerRow.hidden);
  [...ui.tableGrid.querySelectorAll('input')].forEach((el, i) => el.value = currentExercise().answers[i]);
  ui.tableSubmitBtn.click(); check('table submission works', state.score === 1 && state.answered && ui.tableSubmitBtn.disabled);
  ui.nextBtn.click(); check('second table can be submitted', !ui.tableSubmitBtn.disabled && !ui.tableSubmitBtn.hidden);
  ui.tableGrid.querySelector('input').dispatchEvent(new KeyboardEvent('keydown', {key:'Enter', bubbles:true}));
  check('Enter submits verb table', state.answered);
  ui.category.value = 'nouns'; ui.mode.value = 'table'; ui.startBtn.click();
  check('empty set has message and disabled controls', state.exercises.length === 0 && ui.promptText.textContent.includes('No exercises available') && ui.nextBtn.disabled && ui.submitBtn.disabled && ui.tableSubmitBtn.hidden && ui.answerRow.hidden);
  ui.category.value = 'verbs'; ui.mode.value = 'multiple-choice'; ui.count.value = 2; ui.startBtn.click();
  check('choices render and input is hidden', ui.choiceList.children.length >= 2 && ui.answerRow.hidden && !ui.choiceList.hidden);
  const correctIndex = currentExercise().choices.indexOf(currentExercise().answers[0]);
  ui.choiceList.querySelector(`[data-choice="${correctIndex}"]`).click();
  check('choice label does not affect grading', state.score === 1 && ui.choiceList.querySelector('.correct .choice-mark').textContent === '✓');
  ui.nextBtn.click(); ui.revealBtn.click();
  check('reveal shows revision without scoring', state.score === 1 && !ui.revisionPanel.hidden && [...ui.choiceList.querySelectorAll('button')].every(el => el.disabled));
  const oldScore = state.score; submitChoice(currentExercise().answers[0]); check('cannot score after revealing', state.score === oldScore);
  ui.bankSearch.value = 'bog'; ui.bankSearch.dispatchEvent(new Event('input'));
  check('word bank finds Danish words', state.bankItems.length > 0 && state.bankItems.every(item => normalize(item.title + ' ' + item.detail).includes('bog')));
  ui.bankSearch.value = 'zzzzzzzzzzzzzz'; ui.bankSearch.dispatchEvent(new Event('input'));
  check('empty search has message', state.bankItems.length === 0 && ui.bankPageSummary.textContent.includes('No matching'));
  ui.bankSearch.value = 'book'; ui.bankSearch.dispatchEvent(new Event('input')); check('word bank finds English', state.bankItems.length > 0);
  ui.bankCategory.value = 'adjectives'; ui.bankCategory.dispatchEvent(new Event('change')); check('search respects category', state.bankItems.every(item => item.group === 'adjectives'));
  ui.bankSearch.value = ''; ui.bankCategory.value = 'all'; renderBank();
  setTranslateOutput('i går', 'da'); check('Danish translation has audio control', !ui.translateSpeakBtn.hidden && !ui.translateCopyBtn.disabled);
  setTranslateOutput('yesterday', 'en'); check('English translation has no Danish audio', ui.translateSpeakBtn.hidden);
  ui.translateClearBtn.click(); check('clear disables translation controls', ui.translateSpeakBtn.hidden && ui.translateCopyBtn.disabled && !state.translationText);
  setTranslateMode('da-en'); check('direction accessible state', document.querySelector('[data-mode="da-en"]').getAttribute('aria-pressed') === 'true');
  const realFetch = window.fetch;
  window.fetch = async () => ({ok:true, json:async () => [[['i går']], null, 'en']});
  setTranslateMode('en-da'); ui.translateInput.value = 'yesterday'; await runTranslationLookup();
  check('translation success updates result and audio', ui.translateOutput.textContent === 'i går' && !ui.translateSpeakBtn.hidden && !ui.translateBtn.disabled);
  window.fetch = async () => { throw new Error('offline test'); }; await runTranslationLookup();
  check('translation failure recovers controls', ui.translateStatus.textContent.includes('Translation failed') && !ui.translateBtn.disabled);
  window.fetch = realFetch;
  if (danishVoice) {
   const originalSpeak = window.speechSynthesis.speak;
   let utterance;
   window.speechSynthesis.speak = value => { utterance = value; };
   const button = ui.translateSpeakBtn;
   speakDanish('i går', button);
   check('speech requests Danish text and language', utterance?.text === 'i går' && utterance.lang === 'da-DK' && utterance.voice === danishVoice && button.classList.contains('speaking'));
   stopSpeech(); check('stopping speech clears playing state', !button.classList.contains('speaking'));
   window.speechSynthesis.speak = originalSpeak;
  }
  for (const pack of EXERCISE_PACKS) {
   buildSessionFromPack(pack.id);
   const expected = Math.min(pack.count, flattenExercises(pack.category, pack.mode, pack.templateIds).length);
   if (!expected) {
    check(`empty pack is disabled: ${pack.id}`, document.querySelector(`[data-pack-id="${pack.id}"]`).disabled && ui.nextBtn.disabled && ui.promptText.textContent.includes('No exercises available'));
    continue;
   }
   check(`pack count: ${pack.id}`, state.exercises.length === expected && expected > 1);
   const visited = new Set();
   for (let step = 0; !state.complete && step < 101; step++) { visited.add(state.currentIndex); revealAnswer(); nextQuestion(); }
   check(`pack completes all questions: ${pack.id}`, state.complete && visited.size === expected);
   await new Promise(resolve => setTimeout(resolve, 0));
  }
  document.getElementById('openBuilderBtn').click();
  check('custom builder opens', document.getElementById('builderDialog').open);
  document.getElementById('builderMode').value = 'random'; document.getElementById('builderMode').dispatchEvent(new Event('change'));
  document.getElementById('builderClear').click();
  check('builder prevents empty quiz', document.getElementById('startCustomBtn').disabled);
  for (const id of ['verb-en-da-past','noun-en-da-pl']) document.querySelector(`[data-template="${id}"]`).checked = true;
  document.getElementById('builderCount').value = 7;
  document.getElementById('builderCount').dispatchEvent(new Event('input'));
  check('builder previews matching pool', !document.getElementById('startCustomBtn').disabled && document.getElementById('builderPreview').textContent.includes('7 in your session'));
  document.getElementById('saveBuilderBtn').click();
  check('builder saves selected forms', JSON.parse(localStorage.getItem('danish-practice-builder')).ids.length === 2);
  document.getElementById('startCustomBtn').click();
  check('custom quiz has requested count and only selected forms', !document.getElementById('builderDialog').open && state.exercises.length === 7 && state.exercises.every(e => ['verb-en-da-past','noun-en-da-pl'].includes(e.templateId)));
  const customVisited = new Set(); for (let step = 0; !state.complete && step < 101; step++) { customVisited.add(state.currentIndex); nextQuestion(); }
  check('custom quiz advances through all seven questions', state.complete && customVisited.size === 7);
  document.getElementById('openBuilderBtn').click();
  document.getElementById('builderMode').value = 'table'; document.getElementById('builderMode').dispatchEvent(new Event('change')); document.getElementById('builderSelectAll').click();
  document.getElementById('builderCount').value = 5; refreshBuilderPreview(); document.getElementById('startCustomBtn').click();
  check('custom table quiz has five tables', state.exercises.length === 5 && state.exercises.every(e => e.kind === 'Table'));
  check('all bundled categories loaded', Object.keys(window.DANISH_LEXICON).every(c => vocabulary[c].length >= window.DANISH_LEXICON[c].length));
  initializeBuilder();
  check('saved custom setup restores', builderTemplateIds().length === 2 && document.getElementById('builderCount').value === '7');
  document.getElementById('addWordBtn').click();
  document.getElementById('wordCategory').value = 'adverbs'; document.getElementById('wordCategory').dispatchEvent(new Event('change'));
  document.getElementById('word-base').value = 'browser-test-word'; document.getElementById('word-english').value = 'test translation';
  document.getElementById('wordForm').requestSubmit();
  check('Add word saves and closes', !document.getElementById('wordDialog').open && vocabulary.adverbs.some(e => e.base === 'browser-test-word'));
  vocabulary.adverbs = vocabulary.adverbs.filter(e => e.base !== 'browser-test-word'); restoreAddedWords();
  check('added word survives vocabulary reload', vocabulary.adverbs.some(e => e.base === 'browser-test-word'));
  vocabulary.adverbs = vocabulary.adverbs.filter(e => e.base !== 'browser-test-word'); localStorage.removeItem('danish-practice-added-words');
  ui.bankSearch.value = ''; ui.bankCategory.value = 'all'; renderBank();
  check('dashboard stylesheet loaded', getComputedStyle(document.querySelector('.score-ring')).borderRadius === '50%');
  const beforeImport = vocabulary;
  applyImportedLexicon({...vocabulary, common_phrases:[{danish:'God morgen',english:'Good morning'}]});
  check('new phrases enable their pack', !document.querySelector('[data-pack-id="phrases"]').disabled);
  buildSessionFromPack('phrases');
  check('short sets report actual size', state.exercises.length === 2 && ui.feedback.textContent.includes('Only 2 matching questions'));
  nextQuestion(); nextQuestion(); check('short sets still complete', state.complete);
  applyImportedLexicon(beforeImport);
  const saved = vocabulary.nouns;
  vocabulary.nouns = [{singular_indefinite: '<img src=x onerror="window.injection=true">', english: '<b>bad</b>', singular_definite:'x', plural_indefinite:'x', plural_definite:'x', gender:'en'}];
  ui.bankCategory.value = 'nouns'; renderBank(); check('imported text is escaped', !ui.bankList.querySelector('img, b') && !window.injection);
  vocabulary.nouns = saved; ui.bankCategory.value = 'all';
  renderBank();
  resetSession(); check('reset clears session and revision', !state.exercises.length && ui.revisionPanel.hidden && ui.sessionProgress.value === 0 && ui.statScore.textContent === '0 / 0');
  // Capture a representative answered multiple-choice state.
  ui.category.value = 'verbs'; ui.mode.value = 'multiple-choice'; ui.count.value = 12; ui.seed.value = 'preview'; buildSession(['verb-en-da-past']);
  const previewRecord = vocabulary.verbs.find(item => item.infinitive === 'at være');
  const previewQuestion = flattenExercises('verbs','forms',['verb-en-da-past']).find(item => item.record === previewRecord);
  state.exercises[0] = buildChoiceExercise(previewQuestion, mulberry32(2)); renderCurrent(); submitChoice(currentExercise().answers[0]);
  setTranslateMode('en-da'); setTranslateOutput('i går','da'); ui.translateStatus.textContent = ''; ui.translateStatus.className = 'feedback';
  ui.nextBtn.blur(); window.scrollTo(0, 0);
  check('viewport matches requested size', innerWidth === EXPECTED_WIDTH);
  check('no horizontal document overflow', document.documentElement.scrollWidth <= window.innerWidth);
  check('word bank follows quiz and sidebar', ui.bankPanel.getBoundingClientRect().top >= document.querySelector('.layout-split').getBoundingClientRect().bottom);
  check('pagination stays compact', ui.bankPagination.querySelectorAll('button').length <= 7);
  check('no runtime errors', !(window.runtimeErrors || []).length);
 } catch (e) { checks.push({name: 'uncaught test error', passed:false, error: e.stack}); }
  const result = document.createElement('pre'); result.hidden = true; result.id = 'verification-result'; result.textContent = JSON.stringify(checks); document.body.append(result);
}, 1500);
</script>
'''

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args): pass
    def do_GET(self):
        if self.path.startswith('/code/__quiz_check.html'):
            content = SOURCE.replace('</body>', TEST + '</body>').encode()
            self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers(); self.wfile.write(content)
        else: super().do_GET()

class CDP:
    def __init__(self, url):
        parsed = urlsplit(url)
        self.sock = socket.create_connection((parsed.hostname, parsed.port), timeout=15)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall(f'GET {parsed.path} HTTP/1.1\r\nHost: {parsed.netloc}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n'.encode())
        response = b''
        while not response.endswith(b'\r\n\r\n'): response += self.sock.recv(1)
        assert b'101' in response.split(b'\r\n')[0], response
        self.seq = 0
    def read(self, length):
        data = b''
        while len(data) < length:
            part = self.sock.recv(length - len(data))
            if not part: raise ConnectionError('Browser disconnected')
            data += part
        return data
    def call(self, method, **params):
        self.seq += 1
        data = json.dumps({'id':self.seq, 'method':method, 'params':params}).encode()
        mask = os.urandom(4)
        length = len(data)
        header = bytes([0x81, 0x80 | length]) if length < 126 else bytes([0x81, 0xfe]) + struct.pack('!H', length)
        self.sock.sendall(header + mask + bytes(byte ^ mask[i % 4] for i, byte in enumerate(data)))
        while True:
            first, second = self.read(2)
            length = second & 127
            if length == 126: length = struct.unpack('!H', self.read(2))[0]
            if length == 127: length = struct.unpack('!Q', self.read(8))[0]
            payload = self.read(length)
            message = json.loads(payload)
            if message.get('id') == self.seq:
                if 'error' in message: raise RuntimeError(message['error'])
                return message.get('result', {})

server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(ROOT)))
threading.Thread(target=server.serve_forever, daemon=True).start()
browser = shutil.which('google-chrome') or shutil.which('chromium') or shutil.which('chrome') or next((str(path) for path in [Path('C:/Program Files/Google/Chrome/Application/chrome.exe'), Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')] if path.exists()), None)
if not browser: raise SystemExit('Install Chrome, Chromium or Edge to run the browser checks.')
failures = 0
with tempfile.TemporaryDirectory(prefix='danish-quiz-') as scratch:
    for label, width, height in [('desktop', 1536, 1024), ('mobile', 390, 844), ('local-file', 1536, 1024)]:
        screenshot = Path(tempfile.gettempdir()) / f'danish-quiz-{label}.png'
        profile = Path(scratch) / label
        args = [browser, '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', f'--user-data-dir={profile}', '--remote-debugging-port=0', '--hide-scrollbars', 'about:blank']
        process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        client = None
        try:
            active_port = profile / 'DevToolsActivePort'
            port = None
            for _ in range(100):
                try:
                    port = int(active_port.read_text().splitlines()[0])
                    break
                except (OSError, ValueError, IndexError):
                    pass
                time.sleep(.1)
            assert port, 'Browser debugging endpoint did not become ready'
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list') as response: pages = json.load(response)
            client = CDP(next(page['webSocketDebuggerUrl'] for page in pages if page['type'] == 'page'))
            client.call('Page.enable')
            client.call('Emulation.setDeviceMetricsOverride', width=width, height=height, deviceScaleFactor=1, mobile=label == 'mobile')
            client.call('Page.addScriptToEvaluateOnNewDocument', source=f'window.EXPECTED_WIDTH = {width};')
            if label == 'local-file':
                client.call('Page.navigate', url=(ROOT / 'code/danish_practice_tool.html').as_uri())
                for _ in range(100):
                    ready = client.call('Runtime.evaluate', expression="document.readyState === 'complete' && typeof ui !== 'undefined'", returnByValue=True)
                    if ready.get('result', {}).get('value'): break
                    time.sleep(.1)
                client.call('Runtime.evaluate', expression=TEST.replace('<script>', '').replace('</script>', ''))
            else:
                client.call('Page.navigate', url=f'http://127.0.0.1:{server.server_port}/code/__quiz_check.html')
            checks = None
            for _ in range(100):
                result = client.call('Runtime.evaluate', expression="document.getElementById('verification-result')?.textContent", returnByValue=True)
                content = result.get('result', {}).get('value')
                if content: checks = json.loads(content); break
                time.sleep(.1)
            assert checks, 'No test results'
            failures += sum(not check['passed'] for check in checks)
            time.sleep(.2)
            image = client.call('Page.captureScreenshot', format='png', captureBeyondViewport=True)
            screenshot.write_bytes(base64.b64decode(image['data']))
            client.call('Runtime.evaluate', expression="document.getElementById('openBuilderBtn').click()")
            time.sleep(.1)
            builder_image = client.call('Page.captureScreenshot', format='png', captureBeyondViewport=False)
            (Path(tempfile.gettempdir()) / f'danish-builder-{label}.png').write_bytes(base64.b64decode(builder_image['data']))
            print(json.dumps({'view':label, 'passed':sum(c['passed'] for c in checks), 'total':len(checks), 'failures':[c for c in checks if not c['passed']], 'screenshot':str(screenshot)}, ensure_ascii=False), flush=True)
        finally:
            if client:
                try: client.call('Browser.close')
                except (OSError, ConnectionError): pass
                client.sock.close()
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=10)
server.shutdown()
raise SystemExit(bool(failures))
