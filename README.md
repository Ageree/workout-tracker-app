# Workout Tracker с голосовым вводом

iOS приложение для трекинга тренировок с возможностью голосового ввода упражнений и автоматической обработкой через AI.

## 📱 О проекте

**Платформа:** iOS (SwiftUI)
**Бэкенд:** Supabase
**Основная фича:** Голосовой ввод тренировок с AI обработкой
**Референс:** [Dropset](https://www.getdropset.app/)

### Ключевые возможности:
- 🎤 Голосовой ввод упражнений, подходов, повторений
- 🤖 AI обработка речи (извлечение RPE, RIR, упражнений)
- 📊 История тренировок
- ✏️ Редактирование тренировок вручную
- 🔐 Авторизация через Supabase Auth
- 🌐 Поддержка русского и английского языка

---

## ✅ Текущий статус проекта

### Backend (Supabase) - 100% готов ✅

- ✅ База данных создана (4 таблицы)
- ✅ Row Level Security настроен
- ✅ Индексы для оптимизации
- ✅ Триггеры и функции
- ✅ Views для аналитики
- ✅ Authentication настроен
- ✅ API ключи получены

**Документация:**
- [supabase/init.sql](supabase/init.sql) - SQL схема
- [supabase/SETUP.md](supabase/SETUP.md) - инструкции по настройке
- [supabase/SCHEMA.md](supabase/SCHEMA.md) - документация структуры БД

### iOS приложение - В разработке 🚧

#### ✅ Создано:

**Модели данных:**
- [x] User.swift
- [x] Workout.swift
- [x] Exercise.swift
- [x] WorkoutSet.swift

**Services:**
- [x] SupabaseService.swift - CRUD операции, авторизация

**Utilities:**
- [x] Config.swift - конфигурация API ключей

**Структура проекта:**
- [x] Models/
- [x] Views/ (структура папок)
- [x] ViewModels/ (структура папок)
- [x] Services/
- [x] Utilities/

#### 🚧 В разработке:

**Авторизация:**
- [ ] AuthViewModel
- [ ] LoginView
- [ ] RegisterView

**Основной функционал:**
- [ ] WorkoutViewModel
- [ ] WorkoutListView
- [ ] WorkoutDetailView
- [ ] WorkoutEditView

**Голосовой ввод:**
- [ ] AudioRecorderService
- [ ] VoiceRecognitionService (iOS Speech Recognition)
- [ ] AIProcessingService (Claude/GPT API)
- [ ] VoiceRecordingView
- [ ] WorkoutConfirmationView

**UI Components:**
- [ ] WorkoutCard
- [ ] ExerciseRow
- [ ] RecordButton

---

## 🚀 Быстрый старт

### 1. Настройка Supabase ✅ ГОТОВО

База данных уже настроена! Credentials находятся в [.env](.env).

**Project Info:**
- URL: https://measgjlyzxnootmkhktj.supabase.co
- Dashboard: https://app.supabase.com/project/measgjlyzxnootmkhktj

### 2. Настройка Xcode проекта

Следуйте инструкциям в [XCODE_SETUP.md](XCODE_SETUP.md):

1. Добавить Supabase Swift SDK через SPM
2. Добавить созданные файлы в проект
3. Проверить компиляцию
4. Протестировать подключение

### 3. Запуск приложения

```bash
# Откройте проект
open "workout tracker app.xcodeproj"

# Или через командную строку
xcodebuild -scheme "workout tracker app" -destination "platform=iOS Simulator,name=iPhone 15 Pro"
```

---

## 📐 Архитектура

### MVVM Pattern

```
Views ←→ ViewModels ←→ Services ←→ Supabase
          ↓
        Models
```

### Структура БД

```
users (профили)
  ↓
workouts (тренировки)
  ↓
exercises (упражнения)
  ↓
workout_sets (подходы с RPE и RIR)
```

---

## 🎯 Roadmap

### MVP (Первая версия)
- [x] Backend и база данных
- [x] Модели данных
- [x] SupabaseService
- [ ] Авторизация (UI + ViewModel)
- [ ] Список тренировок
- [ ] Детальный просмотр тренировки
- [ ] Редактирование тренировок
- [ ] Голосовой ввод
- [ ] AI обработка речи

### Версия 1.1
- [ ] Суперсеты
- [ ] Таймеры отдыха
- [ ] Шаблоны тренировок

### Версия 1.2
- [ ] История и аналитика
- [ ] Графики прогресса

### Версия 2.0
- [ ] AI Чат-ассистент
- [ ] Персонализированные рекомендации

---

## 🛠 Технологии

### iOS
- **SwiftUI** - UI framework
- **Combine** - Reactive programming
- **AVFoundation** - Audio recording
- **Speech** - iOS Speech Recognition

### Backend
- **Supabase** - Database + Auth
- **PostgreSQL** - Database
- **Row Level Security** - Data protection

### AI
- **Claude API** или **OpenAI GPT** - Парсинг тренировок
- **Whisper API** (опционально) - Транскрипция

### Package Dependencies
- [supabase-swift](https://github.com/supabase/supabase-swift) - Supabase SDK

---

## 📂 Структура проекта

```
workout tracker app/
├── Models/                    # Data models
│   ├── User.swift
│   ├── Workout.swift
│   ├── Exercise.swift
│   └── WorkoutSet.swift
├── Views/                     # SwiftUI views
│   ├── Auth/                  # Login, Register
│   ├── Main/                  # Workout list, details
│   ├── Recording/             # Voice recording
│   └── Components/            # Reusable UI components
├── ViewModels/                # Business logic
│   ├── AuthViewModel.swift
│   ├── WorkoutViewModel.swift
│   └── VoiceRecordingViewModel.swift
├── Services/                  # External services
│   ├── SupabaseService.swift
│   ├── AudioRecorderService.swift
│   ├── VoiceRecognitionService.swift
│   └── AIProcessingService.swift
└── Utilities/                 # Helper files
    └── Config.swift

supabase/                      # Database
├── init.sql                   # Database schema
├── SETUP.md                   # Setup instructions
├── SCHEMA.md                  # Database documentation
└── README.md

.env                           # Environment variables (NOT in git)
.gitignore                     # Git ignore rules
PLAN.md                        # Full development plan
XCODE_SETUP.md                 # Xcode setup instructions
README.md                      # This file
```

---

## 🔐 Безопасность

**Секретные данные хранятся в:**
- [.env](.env) - Environment variables
- [Config.swift](workout tracker app/Utilities/Config.swift) - API keys

**⚠️ НИКОГДА НЕ КОММИТЬТЕ:**
- `.env`
- `Config.swift`
- Любые файлы с API ключами

Файл [.gitignore](.gitignore) уже настроен для защиты секретов.

---

## 📖 Документация

- **[PLAN.md](PLAN.md)** - Полный план разработки (3-4 недели)
- **[XCODE_SETUP.md](XCODE_SETUP.md)** - Настройка Xcode проекта
- **[supabase/SETUP.md](supabase/SETUP.md)** - Настройка Supabase
- **[supabase/SCHEMA.md](supabase/SCHEMA.md)** - Структура БД
- **[supabase/init.sql](supabase/init.sql)** - SQL схема

---

## 🤝 Skills

Установленные навыки для AI ассистента:
- ✅ `frontend-design` (Anthropic)
- ✅ `supabase-postgres-best-practices` (Supabase)

---

## 📝 Следующие шаги

1. Откройте [XCODE_SETUP.md](XCODE_SETUP.md)
2. Добавьте файлы в Xcode проект
3. Установите Supabase Swift SDK
4. Запустите проект
5. Сообщите мне когда будет готово, я продолжу с UI!

---

## 🐛 Issues

Если возникли проблемы, проверьте:
- [XCODE_SETUP.md](XCODE_SETUP.md#-troubleshooting) - Troubleshooting
- [supabase/SETUP.md](supabase/SETUP.md#troubleshooting-решение-проблем) - Supabase проблемы

---

## 📞 Контакты

**Supabase Project:** https://app.supabase.com/project/measgjlyzxnootmkhktj

---

**Дата создания:** 25 января 2026
**Версия:** 0.1.0 (MVP in progress)
**Статус:** 🚧 В разработке
