from services.ai_engine import _similarity, _norm_word

pairs = [
    ('отдежда', 'одежда'),
    ('припреатиях', 'предприятиях'),
    ('шица', 'шить'),
    ('рабблотой', 'работой'),
    ('следе', 'следах'),
    ('ошила', 'шила'),
]

from pathlib import Path
lines = []
for a, b in pairs:
    sim = _similarity(_norm_word(a), _norm_word(b))
    lines.append(f"{a} -> {b}: {sim:.2f}")

Path('similarity_check.txt').write_text('\n'.join(lines), encoding='utf-8')
print("Saved to similarity_check.txt")
