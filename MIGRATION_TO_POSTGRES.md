# Миграция на PostgreSQL

## Шаги для перехода на PostgreSQL

### 1. Установка PostgreSQL

Убедитесь, что PostgreSQL установлен на вашем сервере:
```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# Windows
# Скачайте установщик с https://www.postgresql.org/download/windows/
```

### 2. Создание базы данных

```bash
# Войдите в PostgreSQL
sudo -u postgres psql

# Создайте базу данных
CREATE DATABASE demiurg_bot;

# Создайте пользователя (опционально)
CREATE USER demiurg_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE demiurg_bot TO demiurg_user;

# Выйдите
\q
```

### 3. Настройка переменных окружения

Обновите файл `.env`:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=demiurg_bot
DB_USER=postgres
DB_PASSWORD=your_password
```

### 4. Установка зависимостей

```bash
pip install -r requirements.txt
```

Теперь используется `asyncpg` вместо `aiosqlite`.

### 5. Создание таблиц

Таблицы создадутся автоматически при первом запуске бота.

Или создайте их вручную:
```bash
psql -U postgres -d demiurg_bot -f database_schema.sql
```

### 6. Запуск бота

```bash
python main.py
```

Бот автоматически создаст пул соединений к PostgreSQL и инициализирует таблицы.

---

## Изменения в коде

### database.py
- Заменен `aiosqlite` на `asyncpg`
- Используется пул соединений вместо отдельных соединений
- Параметры запросов изменены с `?` на `$1, $2, ...` (синтаксис PostgreSQL)
- `INSERT OR REPLACE` заменен на `INSERT ... ON CONFLICT`

### config.py
- Добавлены настройки PostgreSQL (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)
- Удалена настройка DATABASE_PATH

### requirements.txt
- Заменен `aiosqlite` на `asyncpg`

---

## Проверка подключения

Для проверки подключения к базе данных:

```python
import asyncio
from database import Database

async def test():
    db = Database()
    await db.init_db()
    user = await db.get_user(123456789)  # Замените на реальный telegram_id
    print(user)
    await db.close()

asyncio.run(test())
```

---

## Миграция данных из SQLite (если нужно)

Если у вас уже есть данные в SQLite, можно мигрировать их:

```python
import asyncio
import aiosqlite
from database import Database

async def migrate():
    # Подключение к старой SQLite БД
    async with aiosqlite.connect('bot_database.db') as sqlite_conn:
        sqlite_conn.row_factory = aiosqlite.Row
        
        # Подключение к новой PostgreSQL БД
        pg_db = Database()
        await pg_db.init_db()
        
        # Миграция пользователей
        async with sqlite_conn.execute("SELECT * FROM users") as cursor:
            users = await cursor.fetchall()
            for user in users:
                await pg_db.add_user(
                    user['telegram_id'],
                    user['username'],
                    user['first_name'],
                    user['last_name']
                )
                if user['gift_received']:
                    await pg_db.mark_gift_received(user['telegram_id'])
        
        # Миграция подписок
        async with sqlite_conn.execute("SELECT * FROM subscriptions") as cursor:
            subscriptions = await cursor.fetchall()
            for sub in subscriptions:
                from datetime import datetime
                start_date = datetime.fromisoformat(sub['start_date'])
                end_date = datetime.fromisoformat(sub['end_date'])
                await pg_db.create_subscription(
                    sub['telegram_id'],
                    sub['channel_name'],
                    sub['payment_method'],
                    start_date,
                    end_date,
                    sub['is_active']
                )
        
        # Миграция платежей
        async with sqlite_conn.execute("SELECT * FROM payments") as cursor:
            payments = await cursor.fetchall()
            for payment in payments:
                await pg_db.create_payment(
                    payment['telegram_id'],
                    payment['channel_name'],
                    payment['amount'],
                    payment['payment_id'],
                    payment['status']
                )
        
        # Миграция напоминаний
        async with sqlite_conn.execute("SELECT * FROM reminders") as cursor:
            reminders = await cursor.fetchall()
            for reminder in reminders:
                from datetime import datetime
                reminder_date = datetime.fromisoformat(reminder['reminder_date'])
                await pg_db.create_reminder(
                    reminder['telegram_id'],
                    reminder['channel_name'],
                    reminder_date
                )
                if reminder['reminder_sent']:
                    await pg_db.mark_reminder_sent(
                        reminder['telegram_id'],
                        reminder['channel_name']
                    )
        
        await pg_db.close()
        print("Миграция завершена!")

asyncio.run(migrate())
```

