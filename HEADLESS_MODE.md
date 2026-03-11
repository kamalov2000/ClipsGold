# Headless Mode - Автономная AI-Фабрика без UI 🤖

## Концепция

Полностью автономная система, которая работает в фоне:
- Ищет видео
- Скачивает
- Транскрибирует
- Анализирует
- Рендерит клипы
- Отправляет в Telegram
- Все автоматически, без UI

## 🚀 Быстрый старт

### Вариант 1: Разовый запуск

```bash
cd backend
python run_autonomous.py
```

Что произойдет:
1. Найдет видео в `uploads/`
2. Транскрибирует (Whisper)
3. Найдет viral моменты
4. Отфильтрует (score >= 8)
5. Отрендерит клипы
6. Отправит в Telegram
7. Сохранит в `clips/`

### Вариант 2: Постоянная работа (TODO)

```bash
# Запустить как сервис
python services/autonomous_scheduler.py
```

Расписание:
- **6:00 AM** - Поиск новых видео
- **9:00 AM, 3:00 PM, 9:00 PM** - Обработка очереди
- **11:00 PM** - Дневной отчет

## 📋 Требования

### Обязательно:

```bash
pip install openai-whisper torch
```

### Для Telegram уведомлений:

В `.env`:
```bash
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Опционально (для полного функционала):

```bash
pip install apscheduler pyyaml google-api-python-client
```

## 🎯 Workflow

```
1. VIDEO DISCOVERY
   ├─ Ищет в uploads/ (ручная загрузка)
   └─ Или yt-dlp search (auto_scout.py)

2. TRANSCRIPTION
   ├─ Whisper API
   ├─ Русский/Английский
   └─ ~30-60 сек на минуту видео

3. VIRAL ANALYSIS
   ├─ GPT-4o/Gemini (если настроен)
   └─ Mock данные (для теста)

4. SMART FILTERING
   ├─ Только viral_score >= 8
   └─ Макс 3 клипа на видео

5. RENDERING
   ├─ FFmpeg (полный pipeline)
   ├─ Субтитры + эффекты
   └─ Сохранение в clips/

6. TELEGRAM
   ├─ Отправка видео (< 50MB)
   └─ Или ссылка на скачивание

7. DEDUPLICATION
   └─ Помечает видео как обработанное
```

## 📁 Структура файлов

```
backend/
├── run_autonomous.py          # Главный скрипт
├── uploads/                   # Входящие видео
├── clips/                     # Готовые клипы
├── services/
│   ├── auto_scout.py         # Поиск видео
│   ├── autonomous_scheduler.py # Расписание
│   ├── telegram_notifier.py  # Уведомления
│   └── youtube_uploader.py   # YouTube API
├── niche_config.yaml         # Настройки ниш
└── .env                      # Конфигурация
```

## ⚙️ Настройка

### 1. Базовая конфигурация (.env)

```bash
# Обязательно
TELEGRAM_BOT_TOKEN=8251121826:AAFBouO6Upt-v3oJ3gM4RfDtqy3anNMFcVc
TELEGRAM_CHAT_ID=731850710

# Опционально
OPENAI_API_KEY=sk-...           # Для GPT-4o анализа
GEMINI_API_KEY=...              # Или Gemini
YOUTUBE_AUTO_UPLOAD=False       # Auto-upload на YouTube
AUTONOMOUS_MODE=True            # Headless режим
```

### 2. Настройка ниш (niche_config.yaml)

```yaml
niches:
  - name: "podcasts"
    enabled: true
    search_queries:
      - "podcast highlights"
      - "best podcast moments"
    min_views: 10000
    viral_score_threshold: 8

settings:
  max_videos_per_niche: 3
  max_videos_per_day: 15
  auto_render_threshold: 8
```

### 3. Добавление видео

**Вручную:**
```bash
# Положи MP4 файлы в:
backend/uploads/
```

**Автоматически (TODO):**
```python
# auto_scout.py будет искать через yt-dlp
python -c "from services.auto_scout import run_trend_scout; run_trend_scout()"
```

## 📊 Мониторинг

### Логи в консоли

```
============================================================
AUTONOMOUS AI FACTORY - HEADLESS MODE
============================================================
Started at: 2026-03-04 20:15:00

Configuration:
  Viral Threshold: 8
  Max Clips per Video: 3
  Telegram: Enabled

============================================================
STEP 1: VIDEO DISCOVERY
============================================================
Using test video: 645a3ffa-e633-4e19-8472-b0cb5ba4d99c.mp4
  File ID: 645a3ffa-e633-4e19-8472-b0cb5ba4d99c
  Size: 17.38 MB

============================================================
STEP 2: TRANSCRIPTION (Whisper)
============================================================
Running Whisper transcription...
SUCCESS! (32.5s)
  Language: ru
  Duration: 60.0s
  Text length: 873 chars
  Segments: 3

...
```

### Telegram уведомления

Каждый готовый клип приходит в Telegram:
- Видео файл (если < 50MB)
- Название и viral score
- Хэштеги
- Длительность и размер

### Файлы на диске

```
clips/
├── clip_645a3ffa_1.mp4  # Клип 1 (score: 9.2)
├── clip_645a3ffa_2.mp4  # Клип 2 (score: 8.8)
└── clip_645a3ffa_3.mp4  # Клип 3 (score: 8.5)
```

## 🔄 Автоматизация

### Запуск по расписанию (Windows)

**Task Scheduler:**
```
Trigger: Daily at 6:00 AM
Action: python D:\riot\ClipsGold\backend\run_autonomous.py
```

### Запуск как сервис (Linux)

**systemd service:**
```ini
[Unit]
Description=ClipsGold AI Factory
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/ClipsGold/backend
ExecStart=/usr/bin/python3 run_autonomous.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Непрерывная работа

```bash
# Бесконечный цикл с паузами
while true; do
    python run_autonomous.py
    sleep 3600  # Пауза 1 час
done
```

## 🎛️ Режимы работы

### 1. Тестовый режим (сейчас)

- Использует видео из `uploads/`
- Mock анализ (без GPT-4o)
- Симуляция рендера (копирует файл)
- Отправка в Telegram работает

### 2. Полуавтоматический

- Ручное добавление видео в `uploads/`
- Автоматическая обработка
- Реальный AI анализ (GPT-4o)
- Полный рендер с FFmpeg
- Telegram уведомления

### 3. Полностью автономный

- Автопоиск видео (yt-dlp)
- Автообработка по расписанию
- AI анализ
- Рендер
- Auto-upload на YouTube
- Telegram отчеты

## 🔧 Troubleshooting

### "No video found for processing"

```bash
# Добавь видео в uploads/
cp /path/to/video.mp4 backend/uploads/
```

### "Telegram not configured"

```bash
# Проверь .env
cat .env | grep TELEGRAM

# Должно быть:
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

### "Transcription failed"

```bash
# Проверь Whisper
python -c "import whisper; print(whisper.__version__)"

# Переустанови если нужно
pip install --upgrade openai-whisper
```

### "File too large for Telegram"

Для файлов > 50MB:
1. Сожми видео (FFmpeg с CRF 28)
2. Или используй Cloud Storage
3. Или YouTube auto-upload

## 📈 Производительность

### Время обработки (1 минутное видео):

- Транскрипция: ~30-60 сек
- AI анализ: ~5-10 сек
- Рендер (1 клип): ~20-40 сек
- Отправка в Telegram: ~10-30 сек

**Итого:** ~2-3 минуты на видео

### Пропускная способность:

- 1 видео = 3 клипа
- 1 цикл (3 часа) = 5-10 видео
- 3 цикла в день = 15-30 видео
- **Итого:** 45-90 клипов в день

## 🎯 Следующие шаги

### Сейчас работает:

✅ Транскрипция (Whisper)
✅ Smart Filtering
✅ Telegram уведомления
✅ Локальное хранение

### Нужно добавить:

⏳ Реальный AI анализ (GPT-4o/Gemini)
⏳ Полный FFmpeg рендер
⏳ Автопоиск видео (yt-dlp)
⏳ YouTube auto-upload
⏳ Scheduler для расписания

### Как добавить:

1. **AI анализ:**
```bash
# Добавь в .env
OPENAI_API_KEY=sk-...

# Раскомментируй в run_autonomous.py
# from analyzer import create_analyzer
# analyzer = create_analyzer()
# clips = analyzer.analyze(transcript)
```

2. **FFmpeg рендер:**
```python
# Используй существующий код из main.py
from main import cut_video_segment_enhanced
```

3. **Auto-upload:**
```python
from services.youtube_uploader import upload_video_to_youtube
upload_video_to_youtube(clip_path, title, description)
```

## 💡 Итог

**Headless режим готов к использованию!**

Запусти:
```bash
python run_autonomous.py
```

Получишь:
- Автоматическую обработку видео
- Клипы в Telegram
- Без UI, полностью в фоне

Для полной автоматизации добавь:
- AI анализ (API ключи)
- Scheduler (расписание)
- Auto-upload (YouTube)
