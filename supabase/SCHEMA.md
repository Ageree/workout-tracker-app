# Database Schema Documentation

## Диаграмма структуры БД

```
┌─────────────────────┐
│    auth.users       │ (Managed by Supabase Auth)
│─────────────────────│
│ id (UUID, PK)       │
│ email               │
│ encrypted_password  │
│ ...                 │
└──────────┬──────────┘
           │
           │ 1:1
           │
           ▼
┌─────────────────────┐
│   public.users      │ (User profiles)
│─────────────────────│
│ id (UUID, PK, FK)   │────────┐
│ email               │        │
│ created_at          │        │
│ updated_at          │        │
└─────────────────────┘        │
                               │
                               │ 1:N
                               │
                               ▼
                    ┌─────────────────────┐
                    │  public.workouts    │ (Workout sessions)
                    │─────────────────────│
                    │ id (UUID, PK)       │────────┐
                    │ user_id (FK)        │        │
                    │ date                │        │
                    │ notes               │        │
                    │ duration            │        │
                    │ created_at          │        │
                    │ updated_at          │        │
                    └─────────────────────┘        │
                                                   │
                                                   │ 1:N
                                                   │
                                                   ▼
                                        ┌─────────────────────┐
                                        │ public.exercises    │ (Exercises)
                                        │─────────────────────│
                                        │ id (UUID, PK)       │────────┐
                                        │ workout_id (FK)     │        │
                                        │ name                │        │
                                        │ exercise_order      │        │
                                        │ notes               │        │
                                        │ created_at          │        │
                                        └─────────────────────┘        │
                                                                       │
                                                                       │ 1:N
                                                                       │
                                                                       ▼
                                                            ┌─────────────────────┐
                                                            │ public.workout_sets │ (Sets)
                                                            │─────────────────────│
                                                            │ id (UUID, PK)       │
                                                            │ exercise_id (FK)    │
                                                            │ set_number          │
                                                            │ reps                │
                                                            │ weight              │
                                                            │ rpe (1-10)          │
                                                            │ rir (0+)            │
                                                            │ created_at          │
                                                            └─────────────────────┘
```

---

## Таблицы

### 1. `public.users`

**Назначение:** Профили пользователей (расширяет `auth.users`)

| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | UUID | Primary Key, Foreign Key → auth.users(id) |
| `email` | TEXT | Email пользователя (уникальный) |
| `created_at` | TIMESTAMP | Дата создания профиля |
| `updated_at` | TIMESTAMP | Дата последнего обновления |

**Особенности:**
- Автоматически создается при регистрации через триггер
- Связан 1:1 с auth.users
- RLS: пользователь видит только свой профиль

---

### 2. `public.workouts`

**Назначение:** Тренировочные сессии

| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | UUID | Primary Key |
| `user_id` | UUID | Foreign Key → users(id) |
| `date` | TIMESTAMP | Дата и время тренировки |
| `notes` | TEXT | Заметки о тренировке (опционально) |
| `duration` | INTEGER | Длительность в минутах (опционально) |
| `created_at` | TIMESTAMP | Дата создания записи |
| `updated_at` | TIMESTAMP | Дата последнего изменения |

**Индексы:**
- `idx_workouts_user_id` на `user_id`
- `idx_workouts_date` на `date DESC`
- `idx_workouts_user_date` на `(user_id, date DESC)`

**RLS:** Пользователь видит только свои тренировки

---

### 3. `public.exercises`

**Назначение:** Упражнения внутри тренировки

| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | UUID | Primary Key |
| `workout_id` | UUID | Foreign Key → workouts(id) |
| `name` | TEXT | Название упражнения |
| `exercise_order` | INTEGER | Порядок выполнения (1, 2, 3...) |
| `notes` | TEXT | Заметки об упражнении (опционально) |
| `created_at` | TIMESTAMP | Дата создания |

**Индексы:**
- `idx_exercises_workout_id` на `workout_id`
- `idx_exercises_workout_order` на `(workout_id, exercise_order)`

**RLS:** Доступ через проверку владельца тренировки

---

### 4. `public.workout_sets`

**Назначение:** Подходы для каждого упражнения

| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | UUID | Primary Key |
| `exercise_id` | UUID | Foreign Key → exercises(id) |
| `set_number` | INTEGER | Номер подхода (1, 2, 3...) |
| `reps` | INTEGER | Количество повторений |
| `weight` | NUMERIC(6,2) | Вес в кг/фунтах (опционально) |
| `rpe` | INTEGER | Rate of Perceived Exertion (1-10) |
| `rir` | INTEGER | Reps in Reserve (0+) |
| `created_at` | TIMESTAMP | Дата создания |

**Constraints:**
- `rpe CHECK (rpe >= 1 AND rpe <= 10)`
- `rir CHECK (rir >= 0)`

**Индексы:**
- `idx_sets_exercise_id` на `exercise_id`
- `idx_sets_exercise_number` на `(exercise_id, set_number)`

**RLS:** Доступ через проверку владельца упражнения/тренировки

---

## Views (Представления)

### 1. `workout_details`

**Назначение:** Полная информация о тренировке с join всех связанных таблиц

**Колонки:**
- workout_id, user_id, date, workout_notes, duration
- exercise_id, exercise_name, exercise_order, exercise_notes
- set_id, set_number, reps, weight, rpe, rir

**Использование:**
```sql
SELECT * FROM public.workout_details
WHERE user_id = auth.uid()
ORDER BY date DESC;
```

---

### 2. `workout_summary`

**Назначение:** Статистика по тренировкам

**Колонки:**
- id, user_id, date, duration
- total_exercises (COUNT)
- total_sets (COUNT)
- total_reps (SUM)
- avg_rpe (AVG)

**Использование:**
```sql
SELECT * FROM public.workout_summary
WHERE user_id = auth.uid()
ORDER BY date DESC;
```

---

## Triggers (Триггеры)

### 1. `on_auth_user_created`

**Триггер на:** `auth.users` (AFTER INSERT)

**Функция:** `handle_new_user()`

**Действие:** Автоматически создает запись в `public.users` при регистрации нового пользователя

---

### 2. `set_users_updated_at`

**Триггер на:** `public.users` (BEFORE UPDATE)

**Функция:** `handle_updated_at()`

**Действие:** Автоматически обновляет `updated_at` при изменении записи

---

### 3. `set_workouts_updated_at`

**Триггер на:** `public.workouts` (BEFORE UPDATE)

**Функция:** `handle_updated_at()`

**Действие:** Автоматически обновляет `updated_at` при изменении тренировки

---

## Row Level Security (RLS)

### Политики безопасности

Все таблицы защищены RLS политиками. Каждая таблица имеет 4 политики:

1. **SELECT** - просмотр данных
2. **INSERT** - создание новых записей
3. **UPDATE** - обновление существующих
4. **DELETE** - удаление записей

### Принципы RLS:

**users:**
- Пользователь видит только свой профиль (`auth.uid() = id`)

**workouts:**
- Пользователь видит только свои тренировки (`auth.uid() = user_id`)

**exercises:**
- Доступ через проверку владельца тренировки (JOIN с workouts)

**workout_sets:**
- Доступ через проверку владельца упражнения (JOIN с exercises и workouts)

---

## Пример запросов

### Получить все тренировки пользователя:

```sql
SELECT
  w.*,
  COUNT(DISTINCT e.id) as exercises_count,
  COUNT(s.id) as sets_count
FROM public.workouts w
LEFT JOIN public.exercises e ON e.workout_id = w.id
LEFT JOIN public.workout_sets s ON s.exercise_id = e.id
WHERE w.user_id = auth.uid()
GROUP BY w.id
ORDER BY w.date DESC;
```

### Получить детали конкретной тренировки:

```sql
SELECT
  e.name,
  e.exercise_order,
  json_agg(
    json_build_object(
      'set_number', s.set_number,
      'reps', s.reps,
      'weight', s.weight,
      'rpe', s.rpe,
      'rir', s.rir
    ) ORDER BY s.set_number
  ) as sets
FROM public.exercises e
LEFT JOIN public.workout_sets s ON s.exercise_id = e.id
WHERE e.workout_id = 'workout-id-here'
GROUP BY e.id, e.name, e.exercise_order
ORDER BY e.exercise_order;
```

### Создать полную тренировку:

```sql
-- 1. Создать тренировку
INSERT INTO public.workouts (user_id, date, notes)
VALUES (auth.uid(), NOW(), 'Chest day')
RETURNING id;

-- 2. Добавить упражнение
INSERT INTO public.exercises (workout_id, name, exercise_order)
VALUES ('workout-id', 'Bench Press', 1)
RETURNING id;

-- 3. Добавить подходы
INSERT INTO public.workout_sets (exercise_id, set_number, reps, rpe, rir)
VALUES
  ('exercise-id', 1, 10, 7, 3),
  ('exercise-id', 2, 8, 8, 2),
  ('exercise-id', 3, 8, 8, 2),
  ('exercise-id', 4, 6, 9, 1);
```

---

## Оптимизация

### Созданные индексы:

1. `idx_workouts_user_id` - быстрый поиск тренировок пользователя
2. `idx_workouts_date` - сортировка по дате
3. `idx_workouts_user_date` - комбинированный индекс для фильтрации и сортировки
4. `idx_exercises_workout_id` - получение упражнений тренировки
5. `idx_exercises_workout_order` - сортировка упражнений
6. `idx_sets_exercise_id` - получение подходов упражнения
7. `idx_sets_exercise_number` - сортировка подходов

### Рекомендации:

- Используйте подготовленные views для сложных запросов
- Ограничивайте выборку с помощью LIMIT
- Используйте пагинацию для больших списков
- Кэшируйте частые запросы на клиенте

---

## Миграции

При изменении схемы создавайте отдельные миграционные файлы:

```
supabase/migrations/
├── 20260125_init.sql         (начальная схема)
├── 20260126_add_weight.sql   (будущие изменения)
└── ...
```

Используйте Supabase CLI для управления миграциями:

```bash
supabase migration new add_feature_name
supabase db push
```

---

**Версия схемы:** 1.0
**Дата создания:** 25 января 2026
**Статус:** Готово к использованию
