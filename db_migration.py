#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Миграция базы данных - добавление новых таблиц и полей
Версия: 2.0
"""

import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE = os.getenv('DATABASE', 'bot.db')


def migrate_database():
    """Применить все миграции к базе данных"""
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    print("🔄 Начинаем миграцию базы данных...")
    
    # ========== МИГРАЦИЯ 1: Расширение таблицы orders ==========
    print("📦 Миграция 1: Расширение таблицы orders...")
    
    try:
        # Проверяем, есть ли уже поле status
        cursor.execute("PRAGMA table_info(orders)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'status' not in columns:
            # Создаем новую таблицу с расширенной схемой
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    inventory_id INTEGER NOT NULL,
                    status TEXT DEFAULT 'pending',
                    payment_proof TEXT,
                    payment_details TEXT,
                    confirmed_by INTEGER,
                    confirmed_at TIMESTAMP,
                    rejection_reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (inventory_id) REFERENCES inventory(id),
                    FOREIGN KEY (confirmed_by) REFERENCES admins(user_id)
                )
            """)
            
            # Копируем данные из старой таблицы
            cursor.execute("""
                INSERT INTO orders_new (id, user_id, inventory_id, created_at)
                SELECT id, user_id, inventory_id, created_at FROM orders
            """)
            
            # Удаляем старую таблицу и переименовываем новую
            cursor.execute("DROP TABLE orders")
            cursor.execute("ALTER TABLE orders_new RENAME TO orders")
            
            print("✅ Таблица orders расширена")
        else:
            print("✅ Таблица orders уже обновлена")
    
    except Exception as e:
        print(f"❌ Ошибка при миграции orders: {e}")
        conn.rollback()
        raise
    
    # ========== МИГРАЦИЯ 2: Таблица пользователей ==========
    print("📦 Миграция 2: Создание таблицы users...")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            is_blocked INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            last_activity TIMESTAMP,
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_orders INTEGER DEFAULT 0,
            total_spent INTEGER DEFAULT 0
        )
    """)
    print("✅ Таблица users создана")
    
    # ========== МИГРАЦИЯ 3: Таблица обращений ==========
    print("📦 Миграция 3: Создание таблицы tickets (обращения)...")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            message TEXT NOT NULL,
            status TEXT DEFAULT 'open',
            priority TEXT DEFAULT 'normal',
            admin_response TEXT,
            responded_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            closed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    print("✅ Таблица tickets создана")
    
    # ========== МИГРАЦИЯ 4: Таблица отзывов ==========
    print("📦 Миграция 4: Создание таблицы reviews (отзывы)...")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            order_id INTEGER,
            rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
            comment TEXT,
            is_approved INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
    """)
    print("✅ Таблица reviews создана")
    
    # ========== МИГРАЦИЯ 5: Таблица настроек бота ==========
    print("📦 Миграция 5: Создание таблицы bot_settings...")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bot_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            captcha_enabled INTEGER DEFAULT 0,
            maintenance_mode INTEGER DEFAULT 0,
            welcome_text TEXT DEFAULT 'Добро пожаловать!',
            welcome_media_type TEXT,
            welcome_media_file_id TEXT,
            payment_instructions TEXT DEFAULT 'Инструкции по оплате',
            support_username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Вставляем дефолтные настройки
    cursor.execute("""
        INSERT OR IGNORE INTO bot_settings (id, payment_instructions)
        VALUES (1, 'Реквизиты для оплаты:\n\nКарта: 1234 5678 9012 3456\n\nПосле оплаты отправьте скриншот квитанции.')
    """)
    print("✅ Таблица bot_settings создана")
    
    # ========== МИГРАЦИЯ 6: Таблица администраторов ==========
    print("📦 Миграция 6: Создание таблицы admins...")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            role TEXT DEFAULT 'admin',
            permissions TEXT,
            added_by INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✅ Таблица admins создана")
    
    # ========== МИГРАЦИЯ 7: Таблица рассылок ==========
    print("📦 Миграция 7: Создание таблицы broadcasts...")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS broadcasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            message_text TEXT NOT NULL,
            media_type TEXT,
            media_file_id TEXT,
            button_text TEXT,
            button_url TEXT,
            target_users TEXT DEFAULT 'all',
            status TEXT DEFAULT 'pending',
            sent_count INTEGER DEFAULT 0,
            failed_count INTEGER DEFAULT 0,
            total_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (admin_id) REFERENCES admins(user_id)
        )
    """)
    print("✅ Таблица broadcasts создана")
    
    # ========== МИГРАЦИЯ 8: Таблица логов ==========
    print("📦 Миграция 8: Создание таблицы action_logs...")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS action_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            action_name TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✅ Таблица action_logs создана")
    
    # ========== МИГРАЦИЯ 9: Таблица статистики ==========
    print("📦 Миграция 9: Создание таблицы statistics...")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stat_date TEXT NOT NULL UNIQUE,
            new_users INTEGER DEFAULT 0,
            active_users INTEGER DEFAULT 0,
            orders_created INTEGER DEFAULT 0,
            orders_completed INTEGER DEFAULT 0,
            orders_cancelled INTEGER DEFAULT 0,
            revenue INTEGER DEFAULT 0
        )
    """)
    print("✅ Таблица statistics создана")
    
    # ========== МИГРАЦИЯ 10: Индексы для производительности ==========
    print("📦 Миграция 10: Создание индексов...")
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_approved ON reviews(is_approved)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_date ON action_logs(created_at)")
    
    print("✅ Индексы созданы")
    
    # Сохраняем изменения
    conn.commit()
    conn.close()
    
    print("\n✅ Миграция базы данных завершена успешно!")
    print("📊 База данных готова к работе с новым функционалом\n")


def rollback_migration():
    """Откатить миграцию (для разработки)"""
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    print("⚠️  ОТКАТ МИГРАЦИИ - удаление новых таблиц...")
    
    tables_to_drop = [
        'tickets', 'reviews', 'bot_settings', 'admins', 
        'broadcasts', 'action_logs', 'statistics'
    ]
    
    for table in tables_to_drop:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
            print(f"🗑 Удалена таблица {table}")
        except Exception as e:
            print(f"❌ Ошибка при удалении {table}: {e}")
    
    conn.commit()
    conn.close()
    
    print("✅ Откат миграции завершен")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--rollback':
        rollback_migration()
    else:
        migrate_database()
