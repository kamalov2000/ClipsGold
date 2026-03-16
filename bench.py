import time, requests

BASE = 'http://localhost:8000'
tests = [
    ('SHORT', 'https://youtube.com/watch?v=WsDIWEqbNOc', '4m11s'),
    ('LONG',  'https://youtube.com/watch?v=g6S8rLTVW44', '33min'),
]

results = []
for label, url, dur in tests:
    print('\n' + '='*55)
    print('ТЕСТ: %s (%s)' % (label, dur))
    print('URL:', url)
    t0 = time.time()

    r = requests.post(BASE + '/download-youtube', json={'url': url}, timeout=300)
    t_dl = time.time() - t0
    if r.status_code != 200:
        print('DOWNLOAD FAILED:', r.status_code, r.text[:200])
        results.append((label, dur, t_dl, 0, 0, 'DOWNLOAD FAILED'))
        continue
    file_id = r.json().get('file_id')
    print('[1] Download: %.1fs | file_id=%s' % (t_dl, file_id))

    t1 = time.time()
    r2 = requests.post(BASE + '/transcribe/' + file_id, timeout=2000)
    t_tr = time.time() - t1
    if r2.status_code != 200:
        print('TRANSCRIBE FAILED:', r2.status_code, r2.text[:200])
        results.append((label, dur, t_dl, t_tr, 0, 'TRANSCRIBE FAILED'))
        continue
    d2 = r2.json()
    segs = len(d2.get('segments', []))
    lang = d2.get('language', '?')
    text = d2.get('text', '')
    print('[2] Transcribe: %.1fs | segs=%d | lang=%s' % (t_tr, segs, lang))
    print('    Preview: %s' % text[:200])

    t2 = time.time()
    r3 = requests.post(BASE + '/extract-clips/' + file_id, json={'platform': 'tiktok'}, timeout=120)
    t_cl = time.time() - t2
    clips = []
    if r3.status_code == 200:
        clips = r3.json().get('candidates', [])
    print('[3] Clips: %.1fs | found=%d' % (t_cl, len(clips)))
    for i, c in enumerate(clips[:3]):
        print('    [%d] %s' % (i+1, c.get('title', '?')[:60]))

    total = time.time() - t0
    print('TOTAL: %.1fs' % total)
    results.append((label, dur, t_dl, t_tr, t_cl, len(clips)))

    if label == 'SHORT':
        print('\n--- пауза 5s ---')
        time.sleep(5)

print('\n' + '='*55)
print('ИТОГ')
print('%-6s %-7s %9s %13s %8s %6s %8s' % ('Тест','Длина','Загрузка','Транскрипц','Клипы','Кол','Итого'))
print('-'*60)
for row in results:
    label, dur, t_dl, t_tr, t_cl, clips = row
    if isinstance(clips, str):
        print('%-6s %-7s %9.1fs  ERROR: %s' % (label, dur, t_dl, clips))
    else:
        total = t_dl + t_tr + t_cl
        print('%-6s %-7s %9.1fs %13.1fs %8.1fs %6d %8.0fs' % (
            label, dur, t_dl, t_tr, t_cl, clips, total))
