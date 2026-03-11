# ClipsGold Backend Tests

## Обзор

Набор unit и integration тестов для проверки корректности работы Human-in-the-Loop архитектуры, валидации таймкодов и парсинга JSON.

## Структура тестов

### `tests/test_analyzer.py` - Unit тесты для анализатора

#### TestTimecodeValidation
- ✅ `test_clips_within_video_duration` - Клипы не выходят за пределы видео
- ✅ `test_minimum_clip_duration` - Минимальная длительность клипа (15 сек)
- ✅ `test_short_video_handling` - Обработка коротких видео
- ✅ `test_very_short_video_no_clips` - Видео короче минимума

#### TestJSONStructure
- ✅ `test_required_fields_present` - Все обязательные поля присутствуют
- ✅ `test_field_types` - Корректные типы данных
- ✅ `test_virality_score_range` - Viral score в диапазоне 1-10
- ✅ `test_json_serializable` - JSON сериализуемость
- ✅ `test_emojis_field` - Валидация поля emojis

#### TestAnalyzerValidation
- ✅ `test_negative_start_time_correction` - Коррекция отрицательных таймкодов
- ✅ `test_end_time_exceeds_duration` - Ограничение end_time длительностью видео

#### TestCandidateStorage
- ✅ `test_candidate_structure_for_storage` - Структура для хранения
- ✅ `test_multiple_file_storage` - Хранение для нескольких файлов

#### TestEdgeCases
- ✅ `test_empty_transcription` - Пустая транскрипция
- ✅ `test_zero_duration_video` - Нулевая длительность
- ✅ `test_very_long_video` - Очень длинное видео (2 часа)

### `tests/test_api_endpoints.py` - Integration тесты для API

#### TestAnalyzeEndpoint
- ✅ `test_analyze_stores_candidates_in_memory` - Сохранение в памяти
- ✅ `test_analyze_returns_valid_json_structure` - Валидная JSON структура
- ✅ `test_analyze_validates_timecodes` - Валидация таймкодов
- ✅ `test_analyze_missing_transcription` - Обработка отсутствующей транскрипции

#### TestGetCandidatesEndpoint
- ✅ `test_get_candidates_from_memory` - Получение из памяти
- ✅ `test_get_candidates_from_file_fallback` - Fallback на файл
- ✅ `test_get_candidates_not_found` - 404 для несуществующего файла
- ✅ `test_candidates_structure` - Структура кандидатов

#### TestExtractClipsEndpoint
- ✅ `test_extract_clips_request_structure` - Структура RenderClipRequest
- ✅ `test_platform_parameter_validation` - Валидация platform параметра

#### TestTimecodeValidationIntegration
- ✅ `test_end_to_end_timecode_validation` - E2E валидация таймкодов
- ✅ `test_custom_clips_timecode_validation` - Валидация custom clips

#### TestCandidateStoragePersistence
- ✅ `test_multiple_files_independent_storage` - Независимое хранение

## Запуск тестов

### Установка зависимостей

```bash
cd backend
pip install pytest pytest-asyncio httpx
```

### Запуск всех тестов

```bash
pytest
```

### Запуск с подробным выводом

```bash
pytest -v
```

### Запуск конкретного файла

```bash
pytest tests/test_analyzer.py
```

### Запуск конкретного теста

```bash
pytest tests/test_analyzer.py::TestTimecodeValidation::test_clips_within_video_duration
```

### Запуск с покрытием кода

```bash
pip install pytest-cov
pytest --cov=. --cov-report=html
```

## Что проверяют тесты

### 1. Валидация таймкодов
- ✅ `start_time >= 0`
- ✅ `end_time <= video_duration`
- ✅ `start_time < end_time`
- ✅ `duration >= 15 seconds` (минимум)
- ✅ `duration <= 60 seconds` (максимум)

### 2. Структура JSON
- ✅ Обязательные поля: `start_time`, `end_time`, `title`, `reason`, `virality_score`, `hook`
- ✅ Типы данных: float/int для времени, str для текста, int для score
- ✅ Диапазон viral_score: 1-10
- ✅ JSON сериализуемость

### 3. Хранение кандидатов
- ✅ In-memory storage работает
- ✅ Fallback на файл работает
- ✅ Независимое хранение для разных файлов

### 4. API эндпоинты
- ✅ `/analyze` сохраняет кандидатов
- ✅ `/clips/{file_id}/candidates` возвращает кандидатов
- ✅ `/extract-clips` принимает новые параметры (platform, clip_indices)

## Примеры использования

### Тестирование анализатора

```python
from analyzer import MockAnalyzer

analyzer = MockAnalyzer()
clips = analyzer.analyze_transcription("Test transcription", 120.0)

# Проверка таймкодов
for clip in clips:
    assert clip["start_time"] >= 0
    assert clip["end_time"] <= 120.0
    assert clip["start_time"] < clip["end_time"]
```

### Тестирование API

```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# Анализ
response = client.post("/analyze/test_file?provider=mock")
assert response.status_code == 200

# Получение кандидатов
response = client.get("/clips/test_file/candidates")
assert response.status_code == 200
assert len(response.json()["candidates"]) > 0
```

## CI/CD Integration

Добавьте в `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-asyncio httpx
      - name: Run tests
        run: |
          cd backend
          pytest -v
```

## Troubleshooting

### Проблема: ModuleNotFoundError

```bash
# Решение: Установите backend в editable mode
pip install -e .
```

### Проблема: Тесты не находят файлы

```bash
# Решение: Запускайте pytest из директории backend
cd backend
pytest
```

### Проблема: Async тесты не работают

```bash
# Решение: Установите pytest-asyncio
pip install pytest-asyncio
```

## Расширение тестов

### Добавление нового теста

```python
# tests/test_analyzer.py

class TestNewFeature:
    """Test new feature description"""
    
    def test_new_functionality(self):
        """Test specific aspect"""
        analyzer = MockAnalyzer()
        result = analyzer.new_method()
        
        assert result is not None
        assert isinstance(result, dict)
```

### Добавление фикстуры

```python
# tests/conftest.py

import pytest

@pytest.fixture
def sample_video_data():
    """Provide sample video data for tests"""
    return {
        "duration": 120.0,
        "fps": 30.0,
        "width": 1920,
        "height": 1080
    }
```

## Метрики покрытия

Целевое покрытие кода:
- ✅ `analyzer.py`: 80%+
- ✅ `main.py` (endpoints): 70%+
- ✅ `subtitle_generator_v2.py`: 60%+

Запуск с отчетом:

```bash
pytest --cov=. --cov-report=term-missing
```
