# Supabase Setup Instructions

## Настройка базы данных для Workout Tracker App

Этот файл содержит пошаговые инструкции по настройке Supabase проекта для приложения.

---

## Шаг 1: Запуск SQL скрипта

### Способ 1: Через Supabase Dashboard (Рекомендуется)

1. Откройте ваш проект в [Supabase Dashboard](https://app.supabase.com)
2. Перейдите в раздел **SQL Editor** (слева в меню)
3. Нажмите **New Query**
4. Скопируйте содержимое файла `init.sql` и вставьте в редактор
5. Нажмите **Run** (или Ctrl/Cmd + Enter)
6. Дождитесь выполнения (должно появиться "Success. No rows returned")

### Способ 2: Через Supabase CLI

```bash
# Убедитесь что Supabase CLI установлен
npm install -g supabase

# Войдите в аккаунт
supabase login

# Привяжите проект
supabase link --project-ref YOUR_PROJECT_REF

# Запустите миграцию
supabase db push
```

---

## Шаг 2: Проверка создания таблиц

### В Dashboard:

1. Перейдите в **Table Editor**
2. Вы должны увидеть следующие таблицы:
   - `users`
   - `workouts`
   - `exercises`
   - `workout_sets`

### Через SQL запрос:

```sql
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
```

---

## Шаг 3: Проверка RLS (Row Level Security)

### Проверить что RLS включен:

```sql
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public';
```

Все таблицы должны иметь `rowsecurity = true`

### Проверить политики:

```sql
SELECT schemaname, tablename, policyname, cmd
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;
```

Вы должны увидеть 4 политики для каждой таблицы (SELECT, INSERT, UPDATE, DELETE)

---

## Шаг 4: Настройка Authentication

### 1. Включить Email/Password провайдер:

1. Перейдите в **Authentication** → **Providers**
2. Убедитесь что **Email** провайдер включен
3. Настройки по умолчанию подходят для начала

### 2. Настроить Email Templates (опционально):

1. **Authentication** → **Email Templates**
2. Можете кастомизировать:
   - Confirmation Email (подтверждение регистрации)
   - Magic Link
   - Reset Password

### 3. URL Configuration:

1. **Authentication** → **URL Configuration**
2. Добавьте URL схемы для вашего iOS приложения:
   ```
   Redirect URLs:
   - workouttracker://auth-callback
   - workouttracker://reset-password
   ```

---

## Шаг 5: Получение API ключей

### 1. Найдите ваши ключи:

1. Перейдите в **Settings** → **API**
2. Скопируйте:
   - **Project URL** (например: `https://xxxxx.supabase.co`)
   - **anon public** ключ (это безопасный ключ для клиента)

### 2. Сохраните в безопасном месте:

⚠️ **НЕ КОММИТЬТЕ В GIT!**

Создайте файл `Config.swift` в iOS проекте:

```swift
enum Config {
    static let supabaseURL = "https://xxxxx.supabase.co"
    static let supabaseAnonKey = "your-anon-key-here"
}
```

Добавьте `Config.swift` в `.gitignore`

---

## Шаг 6: Тестирование базы данных

### Создайте тестового пользователя:

1. Перейдите в **Authentication** → **Users**
2. Нажмите **Add user** → **Create new user**
3. Введите email и пароль
4. Убедитесь что **Auto Confirm User** включен (для тестирования)

### Проверьте автоматическое создание профиля:

```sql
SELECT * FROM public.users;
```

Вы должны увидеть автоматически созданную запись для нового пользователя.

### Создайте тестовую тренировку:

```sql
-- Замените USER_ID на id вашего тестового пользователя
INSERT INTO public.workouts (user_id, date, notes)
VALUES ('ваш-user-id-здесь', NOW(), 'Test workout');

-- Получите ID тренировки
SELECT id FROM public.workouts ORDER BY created_at DESC LIMIT 1;

-- Добавьте упражнение
INSERT INTO public.exercises (workout_id, name, exercise_order)
VALUES ('id-тренировки', 'Bench Press', 1);

-- Получите ID упражнения
SELECT id FROM public.exercises ORDER BY created_at DESC LIMIT 1;

-- Добавьте подход
INSERT INTO public.workout_sets (exercise_id, set_number, reps, rpe, rir)
VALUES ('id-упражнения', 1, 10, 8, 2);
```

### Проверьте view с деталями:

```sql
SELECT * FROM public.workout_details LIMIT 10;
```

---

## Шаг 7: Оптимизация и мониторинг

### Проверьте индексы:

```sql
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
```

### Включите Database Logs (опционально):

1. **Settings** → **Database**
2. Включите **Log Connections**
3. Включите **Log Statements**

Это поможет при отладке.

---

## Шаг 8: Безопасность (Production)

### 1. Rate Limiting:

1. **Settings** → **API**
2. Настройте лимиты запросов
   - Например: 100 запросов в минуту на IP

### 2. CAPTCHA (опционально):

1. **Authentication** → **Settings**
2. Включите **Enable Captcha protection**
3. Настройте hCaptcha или reCAPTCHA

### 3. Email Confirmations:

1. **Authentication** → **Settings**
2. Включите **Enable email confirmations**
3. Пользователи должны подтвердить email перед входом

---

## Структура созданной базы данных

### Таблицы:

```
users (профили пользователей)
├── id (UUID, PK)
├── email (TEXT)
├── created_at (TIMESTAMP)
└── updated_at (TIMESTAMP)

workouts (тренировки)
├── id (UUID, PK)
├── user_id (UUID, FK → users)
├── date (TIMESTAMP)
├── notes (TEXT)
├── duration (INTEGER)
├── created_at (TIMESTAMP)
└── updated_at (TIMESTAMP)

exercises (упражнения)
├── id (UUID, PK)
├── workout_id (UUID, FK → workouts)
├── name (TEXT)
├── exercise_order (INTEGER)
├── notes (TEXT)
└── created_at (TIMESTAMP)

workout_sets (подходы)
├── id (UUID, PK)
├── exercise_id (UUID, FK → exercises)
├── set_number (INTEGER)
├── reps (INTEGER)
├── weight (NUMERIC)
├── rpe (INTEGER, 1-10)
├── rir (INTEGER, 0+)
└── created_at (TIMESTAMP)
```

### Views (вспомогательные представления):

- **workout_details** - полная информация о тренировке с упражнениями и подходами
- **workout_summary** - статистика по тренировкам (кол-во упражнений, подходов, средний RPE)

---

## Troubleshooting (Решение проблем)

### Проблема: "permission denied for table"

**Решение:**
```sql
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
```

### Проблема: RLS блокирует запросы

**Проверка:**
```sql
-- Проверить текущего пользователя
SELECT auth.uid();

-- Временно отключить RLS для тестирования (НЕ для production!)
ALTER TABLE workouts DISABLE ROW LEVEL SECURITY;
```

### Проблема: Trigger не срабатывает

**Проверка:**
```sql
-- Проверить существующие триггеры
SELECT * FROM pg_trigger WHERE tgname LIKE '%users%';
```

---

## Следующие шаги

После успешной настройки Supabase:

1. ✅ Скопируйте API ключи в iOS проект
2. ⏭️ Установите Supabase Swift SDK
3. ⏭️ Создайте `SupabaseService.swift`
4. ⏭️ Реализуйте авторизацию
5. ⏭️ Протестируйте CRUD операции

---

## Полезные SQL запросы для разработки

### Очистить все данные (для тестирования):

```sql
-- ВНИМАНИЕ: Удаляет ВСЕ данные!
TRUNCATE TABLE public.workout_sets CASCADE;
TRUNCATE TABLE public.exercises CASCADE;
TRUNCATE TABLE public.workouts CASCADE;
-- users не трогаем, т.к. связан с auth.users
```

### Получить статистику по пользователю:

```sql
SELECT
    u.email,
    COUNT(DISTINCT w.id) as total_workouts,
    COUNT(DISTINCT e.id) as total_exercises,
    COUNT(s.id) as total_sets,
    MIN(w.date) as first_workout,
    MAX(w.date) as last_workout
FROM public.users u
LEFT JOIN public.workouts w ON w.user_id = u.id
LEFT JOIN public.exercises e ON e.workout_id = w.id
LEFT JOIN public.workout_sets s ON s.exercise_id = e.id
GROUP BY u.id, u.email;
```

### Прогресс по упражнению:

```sql
SELECT
    e.name,
    w.date,
    MAX(s.weight) as max_weight,
    MAX(s.reps) as max_reps
FROM public.exercises e
JOIN public.workouts w ON w.id = e.workout_id
JOIN public.workout_sets s ON s.exercise_id = e.id
WHERE e.name ILIKE '%bench press%'
  AND w.user_id = 'your-user-id'
GROUP BY e.name, w.date
ORDER BY w.date DESC;
```

---

## Контакты и поддержка

- [Supabase Documentation](https://supabase.com/docs)
- [Supabase Discord](https://discord.supabase.com)
- [Supabase GitHub](https://github.com/supabase/supabase)

---

**Дата создания:** 25 января 2026
**Версия схемы:** 1.0
**Статус:** ✅ Готово к использованию
