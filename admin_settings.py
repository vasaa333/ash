#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Админ-панель: Настройки бота
"""

import os
import sqlite3
from telebot import types


DATABASE = os.getenv('DATABASE', 'bot.db')


def register_admin_settings_handlers(bot, user_states, user_data):
    """Регистрация обработчиков настроек бота"""
    
    ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))
    
    def is_admin(user_id):
        """Проверка прав администратора"""
        return user_id == ADMIN_ID
    
    
    def get_setting(key, default=''):
        """Получить значение настройки"""
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM bot_settings WHERE key = ?", (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else default
    
    
    def set_setting(key, value):
        """Установить значение настройки"""
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO bot_settings (key, value, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = datetime('now')
        """, (key, value, value))
        conn.commit()
        conn.close()
    
    
    # ========== ГЛАВНОЕ МЕНЮ НАСТРОЕК ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_settings" and is_admin(call.from_user.id))
    def admin_settings_callback(call):
        """Главное меню настроек"""
        bot.answer_callback_query(call.id, "⚙️ Настройки бота")
        show_settings_menu(call.message)
    
    
    def show_settings_menu(message):
        """Показать меню настроек"""
        maintenance = get_setting('maintenance_mode', '0')
        captcha = get_setting('captcha_enabled', '0')
        welcome_msg = get_setting('welcome_message', 'Добро пожаловать!')
        
        text = f"""⚙️ *Настройки бота*

🔧 *Текущие настройки:*

🛠 Режим обслуживания: {'✅ Включён' if maintenance == '1' else '❌ Выключен'}
🤖 Капча: {'✅ Включена' if captcha == '1' else '❌ Выключена'}
👋 Приветственное сообщение: настроено

⚠️ *Режим обслуживания* блокирует доступ обычных пользователей к боту. Только админы могут работать.

🤖 *Капча* требует от новых пользователей пройти проверку перед использованием бота."""
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        # Режим обслуживания
        if maintenance == '1':
            markup.add(types.InlineKeyboardButton(
                "🛠 Выключить режим обслуживания",
                callback_data="setting_maintenance_off"
            ))
        else:
            markup.add(types.InlineKeyboardButton(
                "🛠 Включить режим обслуживания",
                callback_data="setting_maintenance_on"
            ))
        
        # Капча
        if captcha == '1':
            markup.add(types.InlineKeyboardButton(
                "🤖 Выключить капчу",
                callback_data="setting_captcha_off"
            ))
        else:
            markup.add(types.InlineKeyboardButton(
                "🤖 Включить капчу",
                callback_data="setting_captcha_on"
            ))
        
        markup.add(
            types.InlineKeyboardButton("👋 Изменить приветствие", callback_data="setting_welcome"),
            types.InlineKeyboardButton("💰 Реквизиты оплаты", callback_data="setting_payment"),
            types.InlineKeyboardButton("📊 Просмотр всех настроек", callback_data="settings_view_all"),
            types.InlineKeyboardButton("◀️ Админ-панель", callback_data="admin_panel")
        )
        
        bot.edit_message_text(
            text,
            message.chat.id,
            message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    # ========== РЕЖИМ ОБСЛУЖИВАНИЯ ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "setting_maintenance_on" and is_admin(call.from_user.id))
    def maintenance_on_callback(call):
        """Включить режим обслуживания"""
        set_setting('maintenance_mode', '1')
        bot.answer_callback_query(call.id, "✅ Режим обслуживания включён")
        show_settings_menu(call.message)
    
    
    @bot.callback_query_handler(func=lambda call: call.data == "setting_maintenance_off" and is_admin(call.from_user.id))
    def maintenance_off_callback(call):
        """Выключить режим обслуживания"""
        set_setting('maintenance_mode', '0')
        bot.answer_callback_query(call.id, "✅ Режим обслуживания выключен")
        show_settings_menu(call.message)
    
    
    # ========== КАПЧА ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "setting_captcha_on" and is_admin(call.from_user.id))
    def captcha_on_callback(call):
        """Включить капчу"""
        set_setting('captcha_enabled', '1')
        bot.answer_callback_query(call.id, "✅ Капча включена")
        show_settings_menu(call.message)
    
    
    @bot.callback_query_handler(func=lambda call: call.data == "setting_captcha_off" and is_admin(call.from_user.id))
    def captcha_off_callback(call):
        """Выключить капчу"""
        set_setting('captcha_enabled', '0')
        bot.answer_callback_query(call.id, "✅ Капча выключена")
        show_settings_menu(call.message)
    
    
    # ========== ПРИВЕТСТВЕННОЕ СООБЩЕНИЕ ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "setting_welcome" and is_admin(call.from_user.id))
    def welcome_setting_callback(call):
        """Изменить приветственное сообщение"""
        bot.answer_callback_query(call.id)
        user_states[call.from_user.id] = "setting_welcome_message"
        
        current = get_setting('welcome_message', 'Добро пожаловать!')
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="admin_settings"))
        
        bot.edit_message_text(
            f"👋 *Изменить приветственное сообщение*\n\n"
            f"Текущее сообщение:\n"
            f"```\n{current}\n```\n\n"
            f"Отправьте новый текст приветствия (до 500 символов):",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    @bot.message_handler(func=lambda message: is_admin(message.from_user.id) and user_states.get(message.from_user.id) == "setting_welcome_message")
    def handle_welcome_message(message):
        """Обработка нового приветственного сообщения"""
        text = message.text
        
        if len(text) < 5 or len(text) > 500:
            bot.send_message(
                message.chat.id,
                "❌ Длина сообщения должна быть от 5 до 500 символов."
            )
            return
        
        set_setting('welcome_message', text)
        user_states.pop(message.from_user.id, None)
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("◀️ К настройкам", callback_data="admin_settings"))
        
        bot.send_message(
            message.chat.id,
            "✅ Приветственное сообщение обновлено!",
            reply_markup=markup
        )
    
    
    # ========== РЕКВИЗИТЫ ОПЛАТЫ ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "setting_payment" and is_admin(call.from_user.id))
    def payment_setting_callback(call):
        """Изменить реквизиты оплаты"""
        bot.answer_callback_query(call.id)
        user_states[call.from_user.id] = "setting_payment_details"
        
        current = get_setting('payment_details', 'Реквизиты не установлены')
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="admin_settings"))
        
        bot.edit_message_text(
            f"💰 *Изменить реквизиты оплаты*\n\n"
            f"Текущие реквизиты:\n"
            f"```\n{current}\n```\n\n"
            f"Отправьте новые реквизиты (до 1000 символов):",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    @bot.message_handler(func=lambda message: is_admin(message.from_user.id) and user_states.get(message.from_user.id) == "setting_payment_details")
    def handle_payment_details(message):
        """Обработка новых реквизитов оплаты"""
        text = message.text
        
        if len(text) < 10 or len(text) > 1000:
            bot.send_message(
                message.chat.id,
                "❌ Длина реквизитов должна быть от 10 до 1000 символов."
            )
            return
        
        set_setting('payment_details', text)
        user_states.pop(message.from_user.id, None)
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("◀️ К настройкам", callback_data="admin_settings"))
        
        bot.send_message(
            message.chat.id,
            "✅ Реквизиты оплаты обновлены!",
            reply_markup=markup
        )
    
    
    # ========== ПРОСМОТР ВСЕХ НАСТРОЕК ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "settings_view_all" and is_admin(call.from_user.id))
    def settings_view_all_callback(call):
        """Просмотр всех настроек"""
        bot.answer_callback_query(call.id)
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT key, value, updated_at
            FROM bot_settings
            ORDER BY key
        """)
        settings = cursor.fetchall()
        conn.close()
        
        if not settings:
            text = "📊 *Все настройки*\n\nНастройки не установлены."
        else:
            text = "📊 *Все настройки*\n\n"
            for key, value, updated_at in settings:
                short_value = value[:50] + "..." if len(value) > 50 else value
                text += f"• `{key}`: {short_value}\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("◀️ К настройкам", callback_data="admin_settings"))
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    # ========== MIDDLEWARE ДЛЯ ПРОВЕРКИ РЕЖИМА ОБСЛУЖИВАНИЯ ==========
    
    @bot.middleware_handler(update_types=['message'])
    def check_maintenance_mode(bot_instance, message):
        """Проверка режима обслуживания"""
        if message.from_user.id == ADMIN_ID:
            # Админу всегда разрешено
            return
        
        maintenance = get_setting('maintenance_mode', '0')
        if maintenance == '1':
            bot.send_message(
                message.chat.id,
                "🛠 *Технические работы*\n\n"
                "Бот временно недоступен.\n"
                "Ведутся технические работы.\n\n"
                "Приносим извинения за неудобства!",
                parse_mode="Markdown"
            )
            return False  # Блокируем обработку
        
        return True
