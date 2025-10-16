#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Пользовательское меню: Мои заказы, Обращения, Информация, Отзывы
"""

import os
import sqlite3
from datetime import datetime
from telebot import types
import base64


DATABASE = os.getenv('DATABASE', 'bot.db')


def decrypt_data(encrypted_data: str) -> str:
    """Расшифровка данных"""
    return base64.b64decode(encrypted_data.encode('utf-8')).decode('utf-8')


def register_user_menu_handlers(bot, user_states, user_data):
    """Регистрация обработчиков пользовательского меню"""
    
    # ========== МОИ ЗАКАЗЫ ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "my_orders")
    def my_orders_callback(call):
        """Главное меню 'Мои заказы'"""
        bot.answer_callback_query(call.id, "📦 Мои заказы")
        show_my_orders(call.message, call.from_user.id, page=0)
    
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("my_orders_page_"))
    def my_orders_page_callback(call):
        """Пагинация заказов"""
        page = int(call.data.split("_")[-1])
        bot.answer_callback_query(call.id)
        show_my_orders(call.message, call.from_user.id, page)
    
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("view_my_order_"))
    def view_my_order_callback(call):
        """Просмотр детальной информации о заказе"""
        order_id = int(call.data.split("_")[-1])
        bot.answer_callback_query(call.id)
        show_order_details(call.message, call.from_user.id, order_id)
    
    
    def show_my_orders(message, user_id, page=0):
        """Показать список заказов пользователя"""
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Считаем общее количество заказов
        cursor.execute("""
            SELECT COUNT(*) FROM orders WHERE user_id = ?
        """, (user_id,))
        total = cursor.fetchone()[0]
        
        if total == 0:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("◀️ Главное меню", callback_data="start"))
            bot.edit_message_text(
                "📦 *Мои заказы*\n\n"
                "У вас пока нет заказов.\n"
                "Перейдите в каталог, чтобы сделать первый заказ!",
                message.chat.id,
                message.message_id,
                parse_mode="Markdown",
                reply_markup=markup
            )
            conn.close()
            return
        
        # Пагинация: 5 заказов на страницу
        per_page = 5
        offset = page * per_page
        
        cursor.execute("""
            SELECT o.id, p.name, i.weight_grams, i.price_rub, o.status, o.created_at
            FROM orders o
            JOIN inventory i ON o.inventory_id = i.id
            JOIN products p ON i.product_id = p.id
            WHERE o.user_id = ?
            ORDER BY o.created_at DESC
            LIMIT ? OFFSET ?
        """, (user_id, per_page, offset))
        orders = cursor.fetchall()
        conn.close()
        
        # Формируем текст
        status_emoji = {
            'pending': '⏳ Ожидает подтверждения',
            'confirmed': '✅ Подтверждён',
            'cancelled': '❌ Отменён'
        }
        
        text = f"📦 *Мои заказы* (всего: {total})\n\n"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        for order_id, name, weight, price, status, created_at in orders:
            status_text = status_emoji.get(status, status)
            date = datetime.fromisoformat(created_at).strftime("%d.%m.%Y %H:%M")
            
            button_text = f"№{order_id} | {name} {weight}g | {price}₽ | {status_text}"
            markup.add(types.InlineKeyboardButton(
                button_text,
                callback_data=f"view_my_order_{order_id}"
            ))
        
        # Кнопки пагинации
        nav_buttons = []
        if page > 0:
            nav_buttons.append(types.InlineKeyboardButton("◀️ Назад", callback_data=f"my_orders_page_{page-1}"))
        if (page + 1) * per_page < total:
            nav_buttons.append(types.InlineKeyboardButton("Вперёд ▶️", callback_data=f"my_orders_page_{page+1}"))
        
        if nav_buttons:
            markup.row(*nav_buttons)
        
        markup.add(types.InlineKeyboardButton("◀️ Главное меню", callback_data="start"))
        
        bot.edit_message_text(
            text,
            message.chat.id,
            message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    def show_order_details(message, user_id, order_id):
        """Показать детали заказа"""
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT o.id, p.name, c.name as city, d.name as district, i.weight_grams, i.price_rub,
                   o.status, o.created_at, o.confirmed_at, o.rejection_reason,
                   i.data_encrypted
            FROM orders o
            JOIN inventory i ON o.inventory_id = i.id
            JOIN products p ON i.product_id = p.id
            JOIN cities c ON i.city_id = c.id
            JOIN districts d ON i.district_id = d.id
            WHERE o.id = ? AND o.user_id = ?
        """, (order_id, user_id))
        order = cursor.fetchone()
        conn.close()
        
        if not order:
            bot.answer_callback_query(message.chat.id, "❌ Заказ не найден")
            return
        
        order_id, name, city, district, weight, price, status, created_at, confirmed_at, rejection_reason, encrypted_data = order
        
        status_emoji = {
            'pending': '⏳ Ожидает подтверждения',
            'confirmed': '✅ Подтверждён',
            'cancelled': '❌ Отменён'
        }
        
        text = f"📦 *Заказ №{order_id}*\n\n"
        text += f"🛍 Товар: {name}\n"
        text += f"📍 Город: {city}\n"
        text += f"🗺 Район: {district}\n"
        text += f"⚖️ Вес: {weight}g\n"
        text += f"💰 Цена: {price}₽\n"
        text += f"📊 Статус: {status_emoji.get(status, status)}\n"
        text += f"📅 Дата: {datetime.fromisoformat(created_at).strftime('%d.%m.%Y %H:%M')}\n"
        
        if confirmed_at:
            text += f"✅ Подтверждён: {datetime.fromisoformat(confirmed_at).strftime('%d.%m.%Y %H:%M')}\n"
        
        if rejection_reason:
            text += f"\n❌ Причина отказа:\n{rejection_reason}\n"
        
        if status == 'confirmed' and encrypted_data:
            text += f"\n🔒 *Ваши данные для получения товара:*\n"
            text += f"```\n{decrypt_data(encrypted_data)}\n```\n"
            text += "\n⚠️ Не передавайте эти данные третьим лицам!"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("◀️ К списку заказов", callback_data="my_orders"))
        markup.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="start"))
        
        bot.edit_message_text(
            text,
            message.chat.id,
            message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    # ========== МОИ ОБРАЩЕНИЯ (ТИКЕТЫ) ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "my_tickets")
    def my_tickets_callback(call):
        """Главное меню обращений"""
        bot.answer_callback_query(call.id, "💬 Мои обращения")
        show_my_tickets(call.message, call.from_user.id, page=0)
    
    
    @bot.callback_query_handler(func=lambda call: call.data == "create_ticket")
    def create_ticket_callback(call):
        """Создание нового обращения"""
        bot.answer_callback_query(call.id)
        user_states[call.from_user.id] = "awaiting_ticket_text"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="my_tickets"))
        
        bot.edit_message_text(
            "💬 *Создание обращения*\n\n"
            "Опишите вашу проблему или вопрос.\n"
            "Администратор ответит вам в ближайшее время.\n\n"
            "Отправьте текст обращения:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    @bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "awaiting_ticket_text")
    def handle_ticket_text(message):
        """Обработка текста обращения"""
        user_id = message.from_user.id
        text = message.text
        
        if len(text) < 10:
            bot.send_message(
                message.chat.id,
                "❌ Текст обращения слишком короткий. Минимум 10 символов."
            )
            return
        
        if len(text) > 1000:
            bot.send_message(
                message.chat.id,
                "❌ Текст обращения слишком длинный. Максимум 1000 символов."
            )
            return
        
        # Создаём тикет
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO tickets (user_id, subject, message, status, created_at)
            VALUES (?, ?, ?, 'open', datetime('now'))
        """, (user_id, "Обращение пользователя", text))
        
        ticket_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Очищаем состояние
        user_states.pop(user_id, None)
        
        # Уведомляем админа
        admin_id = int(os.getenv('ADMIN_ID', '0'))
        if admin_id:
            try:
                admin_markup = types.InlineKeyboardMarkup()
                admin_markup.add(types.InlineKeyboardButton(
                    "📝 Ответить",
                    callback_data=f"reply_ticket_{ticket_id}"
                ))
                
                bot.send_message(
                    admin_id,
                    f"💬 *Новое обращение №{ticket_id}*\n\n"
                    f"👤 От: {user_id}\n"
                    f"📝 Текст:\n{text}",
                    parse_mode="Markdown",
                    reply_markup=admin_markup
                )
            except:
                pass
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📋 Мои обращения", callback_data="my_tickets"))
        markup.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="start"))
        
        bot.send_message(
            message.chat.id,
            f"✅ Обращение №{ticket_id} создано!\n\n"
            "Администратор ответит вам в ближайшее время.",
            reply_markup=markup
        )
    
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("my_tickets_page_"))
    def my_tickets_page_callback(call):
        """Пагинация обращений"""
        page = int(call.data.split("_")[-1])
        bot.answer_callback_query(call.id)
        show_my_tickets(call.message, call.from_user.id, page)
    
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("view_my_ticket_"))
    def view_my_ticket_callback(call):
        """Просмотр обращения"""
        ticket_id = int(call.data.split("_")[-1])
        bot.answer_callback_query(call.id)
        show_ticket_details(call.message, call.from_user.id, ticket_id)
    
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("reply_ticket_") and not call.data.startswith("reply_ticket_send_"))
    def reply_ticket_user_callback(call):
        """Пользователь отвечает на тикет"""
        ticket_id = int(call.data.split("_")[-1])
        bot.answer_callback_query(call.id)
        
        user_states[call.from_user.id] = f"replying_ticket_{ticket_id}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data=f"view_my_ticket_{ticket_id}"))
        
        bot.edit_message_text(
            f"💬 *Ответ на обращение №{ticket_id}*\n\n"
            "Напишите ваше сообщение:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    @bot.message_handler(func=lambda message: user_states.get(message.from_user.id, "").startswith("replying_ticket_"))
    def handle_ticket_reply(message):
        """Обработка ответа на тикет от пользователя"""
        state = user_states.get(message.from_user.id, "")
        ticket_id = int(state.split("_")[-1])
        reply_text = message.text
        
        if len(reply_text) < 5:
            bot.send_message(
                message.chat.id,
                "❌ Сообщение слишком короткое. Минимум 5 символов."
            )
            return
        
        # Обновляем тикет - добавляем ответ пользователя к message
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT message FROM tickets WHERE id = ?", (ticket_id,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            bot.send_message(message.chat.id, "❌ Обращение не найдено")
            user_states.pop(message.from_user.id, None)
            return
        
        old_message = result[0]
        updated_message = f"{old_message}\n\n--- Ответ пользователя ---\n{reply_text}"
        
        cursor.execute("""
            UPDATE tickets 
            SET message = ?, status = 'answered', updated_at = datetime('now')
            WHERE id = ?
        """, (updated_message, ticket_id))
        
        conn.commit()
        conn.close()
        
        # Очищаем состояние
        user_states.pop(message.from_user.id, None)
        
        # Уведомляем админа
        admin_id = int(os.getenv('ADMIN_ID', '0'))
        if admin_id:
            try:
                bot.send_message(
                    admin_id,
                    f"💬 *Новый ответ на обращение №{ticket_id}*\n\n"
                    f"👤 От: {message.from_user.id}\n"
                    f"📝 Текст:\n{reply_text}",
                    parse_mode="Markdown"
                )
            except:
                pass
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("◀️ К обращению", callback_data=f"view_my_ticket_{ticket_id}"))
        markup.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="start"))
        
        bot.send_message(
            message.chat.id,
            "✅ Ваш ответ отправлен!\n\nАдминистратор получит уведомление.",
            reply_markup=markup
        )
    
    
    def show_my_tickets(message, user_id, page=0):
        """Показать список обращений пользователя"""
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM tickets WHERE user_id = ?
        """, (user_id,))
        total = cursor.fetchone()[0]
        
        text = f"💬 *Мои обращения* (всего: {total})\n\n"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("➕ Создать обращение", callback_data="create_ticket"))
        
        if total == 0:
            markup.add(types.InlineKeyboardButton("◀️ Главное меню", callback_data="start"))
            bot.edit_message_text(
                text + "У вас пока нет обращений.",
                message.chat.id,
                message.message_id,
                parse_mode="Markdown",
                reply_markup=markup
            )
            conn.close()
            return
        
        # Пагинация: 5 на страницу
        per_page = 5
        offset = page * per_page
        
        cursor.execute("""
            SELECT id, subject, status, created_at
            FROM tickets
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (user_id, per_page, offset))
        tickets = cursor.fetchall()
        conn.close()
        
        status_emoji = {
            'open': '🟢 Открыто',
            'answered': '🔵 Есть ответ',
            'closed': '⚫️ Закрыто'
        }
        
        for ticket_id, subject, status, created_at in tickets:
            date = datetime.fromisoformat(created_at).strftime("%d.%m.%Y %H:%M")
            button_text = f"№{ticket_id} | {status_emoji.get(status, status)} | {date}"
            markup.add(types.InlineKeyboardButton(
                button_text,
                callback_data=f"view_my_ticket_{ticket_id}"
            ))
        
        # Пагинация
        nav_buttons = []
        if page > 0:
            nav_buttons.append(types.InlineKeyboardButton("◀️ Назад", callback_data=f"my_tickets_page_{page-1}"))
        if (page + 1) * per_page < total:
            nav_buttons.append(types.InlineKeyboardButton("Вперёд ▶️", callback_data=f"my_tickets_page_{page+1}"))
        
        if nav_buttons:
            markup.row(*nav_buttons)
        
        markup.add(types.InlineKeyboardButton("◀️ Главное меню", callback_data="start"))
        
        bot.edit_message_text(
            text,
            message.chat.id,
            message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    def show_ticket_details(message, user_id, ticket_id):
        """Показать детали обращения"""
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, subject, message, status, created_at, admin_response, updated_at
            FROM tickets
            WHERE id = ? AND user_id = ?
        """, (ticket_id, user_id))
        ticket = cursor.fetchone()
        conn.close()
        
        if not ticket:
            bot.answer_callback_query(message.chat.id, "❌ Обращение не найдено")
            return
        
        ticket_id, subject, msg, status, created_at, admin_response, updated_at = ticket
        
        status_emoji = {
            'open': '🟢 Открыто',
            'answered': '🔵 Есть ответ',
            'closed': '⚫️ Закрыто'
        }
        
        text = f"💬 *Обращение №{ticket_id}*\n\n"
        text += f"📋 Тема: *{subject}*\n"
        text += f"📊 Статус: {status_emoji.get(status, status)}\n"
        text += f"📅 Создано: {datetime.fromisoformat(created_at).strftime('%d.%m.%Y %H:%M')}\n\n"
        text += f"━━━━━━━━━━━━━━━\n\n"
        
        # Форматируем ваше сообщение как цитату
        text += f"👤 *Вы:*\n"
        for line in msg.split('\n'):
            text += f"┃ {line}\n"
        text += f"🕐 {datetime.fromisoformat(created_at).strftime('%d.%m.%Y %H:%M')}\n"
        
        if admin_response:
            text += f"\n━━━━━━━━━━━━━━━\n\n"
            text += f"👨‍💼 *Администратор:*\n"
            for line in admin_response.split('\n'):
                text += f"┃ {line}\n"
            if updated_at:
                text += f"🕐 {datetime.fromisoformat(updated_at).strftime('%d.%m.%Y %H:%M')}\n"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        if status != 'closed':
            markup.add(types.InlineKeyboardButton("📝 Ответить", callback_data=f"reply_ticket_{ticket_id}"))
        markup.add(types.InlineKeyboardButton("◀️ К списку обращений", callback_data="my_tickets"))
        markup.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="start"))
        
        bot.edit_message_text(
            text,
            message.chat.id,
            message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    # ========== ИНФОРМАЦИЯ ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "info")
    def info_callback(call):
        """Информация о боте"""
        bot.answer_callback_query(call.id, "ℹ️ Информация")
        
        text = """ℹ️ *Информация о боте*

🛍 *Добро пожаловать в наш магазин!*

📋 *Правила использования:*
1. Выберите товар из каталога
2. Укажите город и район доставки
3. Выберите нужный вес
4. Оплатите по указанным реквизитам
5. Отправьте скриншот оплаты
6. Дождитесь подтверждения от администратора
7. Получите данные для получения товара

⚠️ *Важно:*
• Не передавайте данные третьим лицам
• Сохраняйте конфиденциальность
• При проблемах создайте обращение в поддержку
• Администратор проверяет оплату вручную

🔒 *Безопасность:*
• Все данные зашифрованы
• Оплата проверяется администратором
• Личные данные не передаются третьим лицам

💬 *Поддержка:*
• Используйте раздел "Мои обращения"
• Ответ обычно приходит в течение 24 часов

📦 *Доставка:*
• Используем систему закладок
• Точные координаты после подтверждения оплаты
• Гарантия качества товара

⚡️ *Быстрый старт:*
1. Перейдите в "Каталог"
2. Выберите нужный товар
3. Следуйте инструкциям

Спасибо, что выбрали нас! 🎉"""
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("◀️ Главное меню", callback_data="start"))
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    # ========== ОТЗЫВЫ ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "reviews")
    def reviews_callback(call):
        """Главное меню отзывов"""
        bot.answer_callback_query(call.id, "⭐️ Отзывы")
        show_reviews(call.message, call.from_user.id, page=0)
    
    
    @bot.callback_query_handler(func=lambda call: call.data == "leave_review")
    def leave_review_callback(call):
        """Оставить отзыв"""
        bot.answer_callback_query(call.id)
        
        # Проверяем, есть ли у пользователя подтверждённые заказы
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM orders
            WHERE user_id = ? AND status = 'confirmed'
        """, (call.from_user.id,))
        confirmed_orders = cursor.fetchone()[0]
        conn.close()
        
        if confirmed_orders == 0:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("◀️ К отзывам", callback_data="reviews"))
            
            bot.edit_message_text(
                "⚠️ Вы можете оставить отзыв только после успешного заказа.\n\n"
                "Сделайте заказ в каталоге, и после подтверждения администратором "
                "вы сможете оставить отзыв!",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
            return
        
        user_states[call.from_user.id] = "awaiting_review_rating"
        
        markup = types.InlineKeyboardMarkup(row_width=5)
        for i in range(1, 6):
            markup.add(types.InlineKeyboardButton(
                f"{'⭐️' * i}",
                callback_data=f"review_rating_{i}"
            ))
        markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="reviews"))
        
        bot.edit_message_text(
            "⭐️ *Оставить отзыв*\n\n"
            "Сначала выберите оценку от 1 до 5 звёзд:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("review_rating_"))
    def review_rating_callback(call):
        """Обработка выбора рейтинга"""
        rating = int(call.data.split("_")[-1])
        user_data[call.from_user.id] = {'review_rating': rating}
        user_states[call.from_user.id] = "awaiting_review_text"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="reviews"))
        
        bot.edit_message_text(
            f"⭐️ *Оставить отзыв*\n\n"
            f"Ваша оценка: {'⭐️' * rating}\n\n"
            f"Теперь напишите текст отзыва (10-500 символов):",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
        bot.answer_callback_query(call.id)
    
    
    @bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "awaiting_review_text")
    def handle_review_text(message):
        """Обработка текста отзыва"""
        user_id = message.from_user.id
        text = message.text
        
        if len(text) < 10:
            bot.send_message(
                message.chat.id,
                "❌ Текст отзыва слишком короткий. Минимум 10 символов."
            )
            return
        
        if len(text) > 500:
            bot.send_message(
                message.chat.id,
                "❌ Текст отзыва слишком длинный. Максимум 500 символов."
            )
            return
        
        rating = user_data.get(user_id, {}).get('review_rating', 5)
        
        # Сохраняем отзыв
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Проверяем, не оставлял ли пользователь отзыв недавно (в течение дня)
        cursor.execute("""
            SELECT COUNT(*) FROM reviews
            WHERE user_id = ? AND created_at > datetime('now', '-1 day')
        """, (user_id,))
        recent = cursor.fetchone()[0]
        
        if recent > 0:
            conn.close()
            bot.send_message(
                message.chat.id,
                "⚠️ Вы уже оставляли отзыв сегодня. Попробуйте завтра!"
            )
            user_states.pop(user_id, None)
            user_data.pop(user_id, None)
            return
        
        cursor.execute("""
            INSERT INTO reviews (user_id, rating, comment, is_approved, created_at)
            VALUES (?, ?, ?, 0, datetime('now'))
        """, (user_id, rating, text))
        
        conn.commit()
        conn.close()
        
        # Очищаем состояние
        user_states.pop(user_id, None)
        user_data.pop(user_id, None)
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📋 Отзывы", callback_data="reviews"))
        markup.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="start"))
        
        bot.send_message(
            message.chat.id,
            "✅ Спасибо за ваш отзыв!\n\n"
            "После проверки администратором он будет опубликован.",
            reply_markup=markup
        )
    
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("reviews_page_"))
    def reviews_page_callback(call):
        """Пагинация отзывов"""
        page = int(call.data.split("_")[-1])
        bot.answer_callback_query(call.id)
        show_reviews(call.message, call.from_user.id, page)
    
    
    def show_reviews(message, user_id, page=0):
        """Показать отзывы"""
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Считаем одобренные отзывы
        cursor.execute("""
            SELECT COUNT(*) FROM reviews WHERE is_approved = 1
        """)
        total = cursor.fetchone()[0]
        
        text = f"⭐️ *Отзывы клиентов* (всего: {total})\n\n"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("✍️ Оставить отзыв", callback_data="leave_review"))
        
        if total == 0:
            markup.add(types.InlineKeyboardButton("◀️ Главное меню", callback_data="start"))
            bot.edit_message_text(
                text + "Пока нет отзывов. Будьте первым!",
                message.chat.id,
                message.message_id,
                parse_mode="Markdown",
                reply_markup=markup
            )
            conn.close()
            return
        
        # Пагинация: 3 отзыва на страницу
        per_page = 3
        offset = page * per_page
        
        cursor.execute("""
            SELECT rating, comment, created_at
            FROM reviews
            WHERE is_approved = 1
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (per_page, offset))
        reviews = cursor.fetchall()
        conn.close()
        
        for rating, comment, created_at in reviews:
            date = datetime.fromisoformat(created_at).strftime("%d.%m.%Y")
            text += f"{'⭐️' * rating}\n"
            text += f"_{comment}_\n"
            text += f"📅 {date}\n\n"
        
        # Пагинация
        nav_buttons = []
        if page > 0:
            nav_buttons.append(types.InlineKeyboardButton("◀️ Назад", callback_data=f"reviews_page_{page-1}"))
        if (page + 1) * per_page < total:
            nav_buttons.append(types.InlineKeyboardButton("Вперёд ▶️", callback_data=f"reviews_page_{page+1}"))
        
        if nav_buttons:
            markup.row(*nav_buttons)
        
        markup.add(types.InlineKeyboardButton("◀️ Главное меню", callback_data="start"))
        
        bot.edit_message_text(
            text,
            message.chat.id,
            message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
