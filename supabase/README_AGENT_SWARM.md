# Agent Swarm Knowledge System

Автоматизированная система сбора, валидации и интеграции научных исследований в knowledge base через мульти-агентную архитектуру.

## Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                        AGENT SWARM                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Research   │───▶│  Extraction  │───▶│  Validation  │       │
│  │   Agent 🔍   │    │   Agent 📖   │    │   Agent ✅   │       │
│  └──────────────┘    └──────────────┘    └──────┬───────┘       │
│         │                                        │               │
│         │         ┌──────────────┐              │               │
│         │         │   Conflict   │◀─────────────┘               │
│         │         │   Agent 🔄   │                              │
│         │         └──────┬───────┘                              │
│         │                │                                      │
│         │         ┌──────▼───────┐                              │
│         └────────▶│  Knowledge   │                              │
│                   │   Base 📚    │                              │
│                   └──────────────┘                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Агенты

### 1. Research Agent (🔍)
**Задача:** Поиск и первичная фильтрация научных источников

**Источники:**
- PubMed E-utilities API
- CrossRef REST API
- RSS feeds (JSCR, MSSE, etc.)

**Критерии фильтрации:**
- Дата публикации (последние 5 лет)
- Тип исследования (RCT, meta-analysis, systematic review)
- Наличие abstract

**Интервал:** Раз в день (86400s)

### 2. Extraction Agent (📖)
**Задача:** Извлечение scientific claims из исследований

**Процесс:**
1. Получение pending источников из очереди
2. NLP анализ через LLM (GPT-4o / Claude)
3. Извлечение структурированных claims

**Извлекаемые поля:**
- Основной claim (на русском)
- Evidence level (1-5)
- Sample size
- Effect size
- Study design
- Limitations
- Key findings

**Интервал:** Каждые 30 минут (1800s)

### 3. Validation Agent (✅)
**Задача:** Проверка качества и достоверности claims

**Проверки:**
- Дублирование (semantic similarity > 0.9)
- Противоречия с существующими claims
- Соответствие evidence level и study design
- Качество источника

**Критерии отклонения:**
- Similarity > 0.9 с существующим claim
- Evidence level < 2 без веских причин
- Противоречие высокоуровневому claim без новых данных

**Интервал:** Каждые 15 минут (900s)

### 4. Knowledge Base Agent (📚)
**Задача:** Интеграция валидированных claims в БД

**Действия:**
1. **Получение pending claims** через `get_pending_embeddings()` RPC
2. **Генерация embedding** через OpenAI API
3. **Обновление статуса** через `update_embedding_status()` RPC
4. **Обновление evidence hierarchy**

**Flow:**
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  get_pending_   │────▶│  OpenAI API      │────▶│  update_        │
│  embeddings()   │     │  generate_embed  │     │  embedding_     │
│  (status:       │     │                  │     │  status()       │
│   processing)   │     │                  │     │  (status:       │
└─────────────────┘     └──────────────────┘     │   completed)    │
                                                  └─────────────────┘
```

**Интервал:** Каждые 10 минут (600s)

**Используемые SQL функции:**
- `get_pending_embeddings(max_results)` - атомарное получение pending записей
- `update_embedding_status(claim_id, embedding, status)` - обновление статуса

### 5. Conflict Agent (🔄)
**Задача:** Выявление и разрешение конфликтующих claims

**Алгоритм:**
1. Semantic search похожих claims
2. LLM анализ на противоречие
3. Создание связи `contradicts`
4. Обновление флагов conflicting_evidence

**Интервал:** Каждый час (3600s)

## Установка

```bash
cd supabase
pip install -r requirements.txt
```

## Настройка окружения

Создайте файл `.env`:

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key

# OpenAI (обязательно для Extraction, Validation, KB agents)
OPENAI_API_KEY=sk-...

# Anthropic (опционально, альтернатива OpenAI)
ANTHROPIC_API_KEY=...

# PubMed (опционально, увеличивает rate limits)
PUBMED_API_KEY=...

# Logging
LOG_LEVEL=INFO
```

## Запуск

### Запуск всех агентов

```bash
python scheduler.py
```

### Запуск одного агента (one-time)

```bash
# Research Agent
python scheduler.py once research

# Extraction Agent
python scheduler.py once extraction

# Validation Agent
python scheduler.py once validation

# KB Agent
python scheduler.py once kb

# Conflict Agent
python scheduler.py once conflict
```

### Запуск всех агентов one-time

```bash
python scheduler.py once
```

### Проверка статуса

```bash
python scheduler.py status
```

## Структура проекта

```
supabase/
├── agents/
│   ├── __init__.py
│   ├── base_agent.py          # Базовый класс для всех агентов
│   ├── research_agent.py      # 🔍 Research Agent
│   ├── extraction_agent.py    # 📖 Extraction Agent
│   ├── validation_agent.py    # ✅ Validation Agent
│   ├── kb_agent.py            # 📚 Knowledge Base Agent
│   └── conflict_agent.py      # 🔄 Conflict Agent
├── services/
│   ├── __init__.py
│   ├── supabase_client.py     # Supabase REST API клиент
│   ├── pubmed_service.py      # PubMed E-utilities API
│   ├── crossref_service.py    # CrossRef REST API
│   ├── rss_service.py         # RSS feed parser
│   └── llm_service.py         # OpenAI/Anthropic LLM
├── config.py                  # Конфигурация
├── scheduler.py               # Планировщик агентов
└── requirements.txt           # Зависимости
```

## Метрики

| Метрика | Цель |
|---------|------|
| Новых claims/неделю | 10-20 |
| Точность extraction | > 85% |
| Ложные positives | < 10% |
| Время обработки | < 5 мин/источник |
| Покрытие тем | +50 за месяц |
| Pending embeddings | < 50 |
| Failed embeddings | < 5% |

## Мониторинг

Агенты логируют свою работу через стандартный logging модуль Python. Уровень логирования настраивается через переменную окружения `LOG_LEVEL`.

Пример логов:
```
2026-01-30 18:30:00 - INFO - [ResearchAgent] Agent started (interval: 86400s)
2026-01-30 18:30:01 - INFO - [ResearchAgent] Starting research search...
2026-01-30 18:30:15 - INFO - [ResearchAgent] Research search complete. Added 12 new sources to queue.
2026-01-30 18:40:00 - INFO - [KnowledgeBaseAgent] Starting knowledge base integration...
2026-01-30 18:40:01 - INFO - [KnowledgeBaseAgent] Found 3 claims to process
2026-01-30 18:40:05 - INFO - [KnowledgeBaseAgent] KB integration complete. Processed 3 claims, generated 3 embeddings
```

### SQL запросы для мониторинга

```sql
-- Статус embedding generation
SELECT 
  embedding_status,
  COUNT(*) as count
FROM scientific_knowledge
GROUP BY embedding_status;

-- Failed embeddings
SELECT 
  id,
  claim,
  embedding_error,
  created_at
FROM scientific_knowledge
WHERE embedding_status = 'failed'
ORDER BY created_at DESC;

-- Очередь на обработку
SELECT COUNT(*) as pending_count
FROM scientific_knowledge
WHERE embedding_status = 'pending';
```

## Риски и митигация

| Риск | Митигация |
|------|-----------|
| Rate limits API | Экспоненциальный backoff |
| Низкое качество extraction | Human-in-the-loop review |
| Дублирование claims | Strict similarity threshold (0.9) |
| Противоречивые данные | Conflict resolution workflow |
| API costs | Caching, batch processing |

## Разработка

### Добавление нового агента

1. Создайте класс, наследующий `BaseAgent`:

```python
from agents.base_agent import BaseAgent

class MyAgent(BaseAgent):
    async def process(self):
        # Your processing logic
        pass
```

2. Добавьте агента в scheduler:

```python
from agents.my_agent import MyAgent

# In AgentScheduler._init_agents()
self.agents['my_agent'] = MyAgent(supabase=self.supabase)
```

3. Настройте интервал в конфигурации:

```python
self.configs['my_agent'] = AgentConfig(
    enabled=True,
    interval_seconds=1800
)
```

## Лицензия

MIT