import re
import time
import math
import asyncio
import hashlib
import secrets
import sqlite3
import logging
from html import escape
from pathlib import Path
from decimal import Decimal, InvalidOperation
from contextlib import suppress
from urllib.parse import urlencode

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (CallbackQuery, InlineKeyboardButton as Button,
    InlineKeyboardMarkup as Keyboard, Message, LinkPreviewOptions, InlineQuery,
    InlineQueryResultArticle, InlineQueryResultsButton, InputTextMessageContent,
    ChosenInlineResult, BusinessConnection, MessageEntity)
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError, TelegramRetryAfter

# ═══════════════════════════════════════════════════════════════
#  ТОКЕН БОТА — впиши сюда токен от @BotFather (без пробелов/кавычек)
#  Получить: https://t.me/BotFather → /newbot или выбери бота → API Token
# ═══════════════════════════════════════════════════════════════
BOT_TOKEN = '9067892123:AAHDLCg00dCgEEbmXOncx7uS1U-LR4OrENI'
# ═══════════════════════════════════════════════════════════════

ROOT = Path(__file__).resolve().parent

# ═══════════════════════════════════════════════════════════════
#  Тексты карточки и алертов — RU / EN
#  Язык оффера: 'ru' (по умолчанию) или 'en' (если в конце 'eng')
# ═══════════════════════════════════════════════════════════════
T = {
    'ru': {
        'tpl_expired':    '🎁 {name} #{number}\n\nСрок действия офера истёк.\n\n🆔 <b>ID сделки:</b> <code>{did}</code>',
        'tpl_new':        'Пользователь {buyer} предлαгαет Вαм {price} зα коллекционный предмет\n<a href="{url}">{name}</a>\n\nДействует {h}ч {m}мин...\n\n🆔 <b>ID сделки:</b> <code>{did}</code>',
        'tpl_accepted':   '🎁 {name} #{number}  успешно\nпродαн!\n\n• Передαйте подαрок покупαтелю для\nзαчисления {price}.\n\n🆔 <b>ID сделки:</b> <code>{did}</code>',
        'tpl_pending':    '🎁 {name} #{number}\n\n⏳ Оплата ожидается.\n\n🆔 <b>ID сделки:</b> <code>{did}</code>',
        'tpl_paid':       '🎁 {name} #{number}\n\n✅ Оплата подтверждена.\n\n🆔 <b>ID сделки:</b> <code>{did}</code>',
        'tpl_declined':   '🎁 {name} #{number}\n\nПредложение отклонено.\n\n🆔 <b>ID сделки:</b> <code>{did}</code>',
        'btn_decline':    '❌ Отклонить',
        'btn_accept':     '✅ Принять',
        'btn_transfer':   'Передαть подαрок',
        'btn_paid':       'Я получил оплату',
        'btn_confirm_yes':'Да, оплата получена',
        'btn_back':       'Назад',
        'alert_accept':        '🎁 {name} #{number} успешно продαн!\n\nПередαйте подαрок покупαтелю для зαчисления {price}.',
        'alert_not_accepted':  'Сначала примите предложение или откройте его актуальную карточку.',
        'alert_confirm_paid':  'Подтвердите, только если вы действительно получили оплату.',
        'alert_status_changed':'Статус уже изменился. Откройте предложение по исходной ссылке.',
        'alert_private_only':  'Откройте предложение в личном чате с ботом.',
        'alert_biz_unavailable':'Бизнес-подключение недоступно.',
        'err_not_found':     'Офер не найден. Попросите автора создать новый.',
        'err_wrong_seller':  'Офер привязан к другому аккаунту продавца. Откройте его с аккаунта, для которого он создан.',
        'err_wrong_target':  'Офер создан для @{target}. Вы вошли как {current}. Проверьте username продавца в запросе.',
        'err_unavailable':   'Офер недоступен для вашего аккаунта.',
        'no_username':       'аккаунт без username',
    },
    'en': {
        'tpl_expired':    '🎁 {name} #{number}\n\nThe offer has expired.\n\n🆔 <b>Deal ID:</b> <code>{did}</code>',
        'tpl_new':        'User {buyer} offers you {price} for a collectible item\n<a href="{url}">{name}</a>\n\nValid for {h}h {m}m...\n\n🆔 <b>Deal ID:</b> <code>{did}</code>',
        'tpl_accepted':   '🎁 {name} #{number} successfully\nsold!\n\n• Send the gift to the buyer to\ncredit {price}.\n\n🆔 <b>Deal ID:</b> <code>{did}</code>',
        'tpl_pending':    '🎁 {name} #{number}\n\n⏳ Awaiting payment.\n\n🆔 <b>Deal ID:</b> <code>{did}</code>',
        'tpl_paid':       '🎁 {name} #{number}\n\n✅ Payment confirmed.\n\n🆔 <b>Deal ID:</b> <code>{did}</code>',
        'tpl_declined':   '🎁 {name} #{number}\n\nOffer declined.\n\n🆔 <b>Deal ID:</b> <code>{did}</code>',
        'btn_decline':    '❌ Decline',
        'btn_accept':     '✅ Accept',
        'btn_transfer':   'Send gift',
        'btn_paid':       'I received payment',
        'btn_confirm_yes':'Yes, payment received',
        'btn_back':       'Back',
        'alert_accept':        '🎁 {name} #{number} successfully sold!\n\nSend the gift to the buyer to credit {price}.',
        'alert_not_accepted':  'Accept the offer first or open its current card.',
        'alert_confirm_paid':  'Confirm only if you have actually received payment.',
        'alert_status_changed':'Status has already changed. Open the offer via the original link.',
        'alert_private_only':  'Open the offer in a private chat with the bot.',
        'alert_biz_unavailable':'Business connection unavailable.',
        'err_not_found':     'Offer not found. Ask the author to create a new one.',
        'err_wrong_seller':  'The offer is linked to another seller account. Open it from the account it was created for.',
        'err_wrong_target':  'The offer was created for @{target}. You are signed in as {current}. Check the seller username.',
        'err_unavailable':   'The offer is not available for your account.',
        'no_username':       'account without username',
    }
}

# ═══════════════════════════════════════════════════════════════
#  Подробная инструкция (показывается по /help и /start setup)
# ═══════════════════════════════════════════════════════════════
GUIDE = (
    '📖 <b>Инструкция по созданию оферов</b>\n\n'
    '<b>1️⃣ Включите inline-режим</b> (если ещё не включён):\n'
    '• Откройте @BotFather → отправьте /setinline\n'
    '• Выберите своего бота\n'
    '• Введите короткое название (например: <code>Поиск оферов</code>)\n'
    '• Подождите 1–2 минуты\n\n'
    '<b>2️⃣ Активируйте доступ</b>:\n'
    '• Отправьте /work → нажмите кнопку «Оставить заявку inline»\n\n'
    '<b>3️⃣ Создайте офер</b>\n\n'
    'Через команду /offer в личке бота:\n'
    '<code>/offer @продавец https://t.me/nft/PlushPepe-2687 20</code>\n'
    '<code>/offer https://t.me/nft/PlushPepe-2687 20</code>\n\n'
    'Через inline-режим (в любом чате):\n'
    '<code>@бот @продавец https://t.me/nft/PlushPepe-2687 20</code>\n'
    '<code>@бот https://t.me/nft/PlushPepe-2687 20</code>\n\n'
    'В бизнес-чате (Secretary Mode):\n'
    '<code>/offer @продавец https://t.me/nft/PlushPepe-2687 20</code>\n'
    '<code>/o https://t.me/nft/PlushPepe-2687 20</code> — короткая команда\n\n'
    '<b>4️⃣ Валюта</b> (по умолчанию <code>stars</code>):\n'
    '<code>/offer URL цена stars</code> — Telegram Stars ⭐️\n'
    '<code>/offer URL цена gram</code> — TON\n\n'
    '<b>5️⃣ Язык</b> (по умолчанию русский):\n'
    '<code>/offer URL цена eng</code> — карточка на английском\n'
    '<code>/offer URL цена stars eng</code> — Stars + английский\n\n'
    '<b>Полный формат:</b>\n'
    '<code>[@продавец] URL цена [stars/gram] [eng]</code>'
)


def offer_lang(o):
    """Возвращает язык оффера: 'ru' или 'en'."""
    if o and 'lang' in o.keys() and o['lang']:
        return o['lang']
    return 'ru'


def parse_offer(args):
    parts = (args or '').split()
    if not parts:
        raise ValueError('Формат: [@продавец] URL цена [stars/gram] [eng]')
    # Языковой суффикс: eng / en (всегда последний)
    lang = 'ru'
    if parts[-1].lower() in ('eng', 'en'):
        parts.pop()
        lang = 'en'
    # Необязательный суффикс валюты: stars / gram / ton
    currency = 'XTR'
    if parts and parts[-1].lower() in ('stars', 'star', 'gram', 'ton'):
        suffix = parts.pop().lower()
        currency = 'TON' if suffix in ('gram', 'ton') else 'XTR'
    # Необязательный префикс @продавец
    target = None
    if parts and parts[0].startswith('@'):
        target = parts[0][1:].lower()
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{3,31}', target):
            raise ValueError('Укажите корректный @username адресата.')
        parts = parts[1:]
    if len(parts) != 2:
        raise ValueError('Укажите URL подарка и цену: https://t.me/nft/PlushPepe-2687 20')
    url, amount = parts
    if not re.fullmatch(r'https://t\.me/nft/[A-Za-z][A-Za-z0-9-]*-\d+', url):
        raise ValueError('Нужна ссылка на коллекционный подарок: https://t.me/nft/Название-Номер')
    try:
        value = Decimal(amount.replace(',', '.'))
        if not value.is_finite() or not Decimal('1') <= value <= Decimal('1000000000') or value != value.to_integral_value():
            raise ValueError()
    except (InvalidOperation, ValueError):
        raise ValueError('Укажите целое положительное количество.')
    return target, url, str(int(value)), currency, lang


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute('''CREATE TABLE IF NOT EXISTS offers (
            id TEXT PRIMARY KEY, buyer INTEGER NOT NULL, username TEXT NOT NULL,
            target TEXT NOT NULL, url TEXT NOT NULL, amount TEXT NOT NULL,
            seller INTEGER, state TEXT NOT NULL DEFAULT 'new')''')
        self.db.commit()
        columns = {r[1] for r in self.db.execute('PRAGMA table_info(offers)')}
        for name, definition in [('currency', "TEXT NOT NULL DEFAULT 'TON'"),
                                 ('expires', 'REAL'), ('sent_at', 'REAL'), ('recipient', 'TEXT'),
                                 ('deal_id', 'TEXT'), ('lang', "TEXT NOT NULL DEFAULT 'ru'")]:
            if name not in columns:
                self.db.execute(f'ALTER TABLE offers ADD COLUMN {name} {definition}')
        self.db.execute('CREATE TABLE IF NOT EXISTS inline_messages (message_id TEXT PRIMARY KEY, offer_id TEXT NOT NULL)')
        self.db.commit()
        self.db.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS inline_offers (fingerprint TEXT PRIMARY KEY, offer_id TEXT NOT NULL)')
        self.db.execute('''CREATE TABLE IF NOT EXISTS business_connections (
            id TEXT PRIMARY KEY, owner INTEGER NOT NULL, enabled INTEGER NOT NULL, can_reply INTEGER NOT NULL)''')
        self.db.execute('''CREATE TABLE IF NOT EXISTS business_messages (
            connection TEXT NOT NULL, chat INTEGER NOT NULL, message INTEGER NOT NULL, offer_id TEXT NOT NULL,
            PRIMARY KEY(connection, chat, message))''')
        self.db.commit()

    def save_connection(self, connection):
        can_reply = bool(connection.rights and connection.rights.can_reply)
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO business_connections VALUES(?,?,?,?)',
                            (connection.id, connection.user.id, connection.is_enabled, can_reply))

    def business_sent(self, key, owner, connection, chat, message):
        offer = self.get(key)
        if not offer or offer['buyer'] != owner:
            return
        now = time.time()
        with self.db:
            self.db.execute('UPDATE offers SET sent_at=?,expires=?,seller=? WHERE id=?',
                            (now, now + 21600, chat, key))
            self.db.execute('INSERT OR IGNORE INTO business_messages VALUES(?,?,?,?)',
                            (connection, chat, message, key))

    def setting(self, key):
        row = self.db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
        return row[0] if row else None

    def set_setting(self, key, value):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (key, value))

    def can_create(self, uid):
        return self.setting(f'creator:{uid}') == 'enabled'

    def request_creator_access(self, uid):
        if not self.can_create(uid):
            self.set_setting(f'creator:{uid}', 'pending')

    def activate_creator(self, uid):
        if self.setting(f'creator:{uid}') not in {'pending', 'enabled'}:
            return False
        self.set_setting(f'creator:{uid}', 'enabled')
        return True

    def inline_offer(self, buyer, username, target, url, amount, currency='XTR', recipient=None, lang='ru'):
        # Telegram sends queries repeatedly while typing; reuse the same offer.
        fingerprint = hashlib.sha256(f'{currency}|{buyer}|{username}|{target or ""}|{url}|{amount}|{recipient or username}|{lang}'.encode()).hexdigest()
        row = self.db.execute('SELECT offer_id FROM inline_offers WHERE fingerprint=?', (fingerprint,)).fetchone()
        if row:
            return self.get(row[0])
        key = self.create(buyer, username, target, url, amount, currency=currency, recipient=recipient, lang=lang)
        with self.db:
            self.db.execute('INSERT INTO inline_offers VALUES (?,?)', (fingerprint, key))
        return self.get(key)

    def create(self, buyer, username, target, url, amount, currency='XTR', recipient=None, lang='ru'):
        key = secrets.token_urlsafe(12)
        deal_id = secrets.token_hex(5)  # 10 hex chars, e.g. "de88ff8184"
        with self.db:
            self.db.execute('INSERT INTO offers(id,deal_id,buyer,username,target,url,amount,currency,expires,recipient,lang) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                            (key, deal_id, buyer, username, target or '', url, amount, currency, time.time() + 21600, recipient or username, lang))
        return key

    def get(self, key):
        return self.db.execute('SELECT * FROM offers WHERE id=?', (key,)).fetchone()

    def mark_sent(self, key, buyer, message_id):
        offer = self.get(key)
        if not offer or offer['buyer'] != buyer:
            return
        now = time.time()
        with self.db:
            self.db.execute('UPDATE offers SET sent_at=?, expires=? WHERE id=? AND sent_at IS NULL AND state="new"',
                            (now, now + 21600, key))
            self.db.execute('INSERT OR IGNORE INTO inline_messages VALUES (?,?)', (message_id, key))

    def allowed(self, offer, uid, username):
        if not offer:
            return False
        if offer['seller'] is not None:
            return offer['seller'] == uid
        if offer['target']:
            return (username or '').lower() == offer['target'] or uid == offer['buyer']
        # Офер без указания адресата — может принять любой, включая автора (тестовый режим).
        return True

    def transition(self, key, uid, username, action):
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            offer = self.get(key)
            if not self.allowed(offer, uid, username):
                return False
            if offer['state'] == 'new' and offer['expires'] and time.time() >= offer['expires']:
                return False
            transitions = {'accept': ('new', 'accepted'), 'decline': ('new', 'declined'),
                           'sent': ('accepted', 'pending'), 'paid': ('pending', 'paid')}
            if action not in transitions:
                return False
            before, after = transitions[action]
            return self.db.execute('UPDATE offers SET state=?,seller=? WHERE id=? AND state=?',
                                   (after, uid, key, before)).rowcount == 1


def gift_recipient(offer):
    return offer['recipient'] or offer['username']


def access_error(offer, user, lang='ru'):
    t = T[lang]
    if not offer:
        return t['err_not_found']
    if offer['seller'] is not None:
        return t['err_wrong_seller']
    if offer['target']:
        current = f'@{user.username}' if user.username else t['no_username']
        return t['err_wrong_target'].format(target=offer['target'], current=current)
    return t['err_unavailable']


def gift_info(o):
    """Извлекает имя подарка и номер из URL вида https://t.me/nft/SnowGlobe-24199."""
    slug = o['url'].rsplit('/', 1)[-1]
    name_part, sep, number = slug.rpartition('-')
    if not sep:
        name_part, number = slug, ''
    # camelCase → "Snow Globe", дефисы в имени → пробелы
    readable = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', name_part).replace('-', ' ')
    return readable, number


def deal_id(o):
    """Короткий hex ID сделки; для старых оферов — детерминированный из ключа."""
    return o['deal_id'] or hashlib.sha256(o['id'].encode()).hexdigest()[:10]


def price(o):
    return f"{o['amount']} {'⭐️ Stars' if o['currency'] == 'XTR' else 'TON'}"


def render(o):
    name, number = gift_info(o)
    did = deal_id(o)
    key = o['id']
    buyer = f'@{o["username"]}'
    t = T[offer_lang(o)]
    rows = []
    p = price(o)

    if o['state'] == 'new' and o['expires'] and time.time() >= o['expires']:
        text = t['tpl_expired'].format(name=escape(name), number=escape(number), did=did)
    elif o['state'] == 'new':
        minutes = min(360, max(0, math.ceil((o['expires'] - time.time()) / 60)))
        hours, mins = minutes // 60, minutes % 60
        text = t['tpl_new'].format(buyer=buyer, price=p, url=o['url'], name=escape(name),
                                   h=hours, m=mins, did=did)
        rows += [[
            Button(text=t['btn_decline'], callback_data=f'decline:{key}',
                   text_entities=[MessageEntity(type='custom_emoji', offset=0, length=1,
                                                custom_emoji_id='5774077015388852135')]),
            Button(text=t['btn_accept'], callback_data=f'accept:{key}',
                   text_entities=[MessageEntity(type='custom_emoji', offset=0, length=1,
                                                custom_emoji_id='5774022692642492953')])
        ]]
    elif o['state'] == 'accepted':
        text = t['tpl_accepted'].format(name=escape(name), number=escape(number), price=p, did=did)
        rows += [[Button(text=t['btn_transfer'], url=f'tg://send_gift?to={o["buyer"]}')]]
    elif o['state'] == 'pending':
        text = t['tpl_pending'].format(name=escape(name), number=escape(number), did=did)
        rows += [[Button(text=t['btn_paid'], callback_data=f'paid:{key}')]]
    elif o['state'] == 'paid':
        text = t['tpl_paid'].format(name=escape(name), number=escape(number), did=did)
    else:  # declined
        text = t['tpl_declined'].format(name=escape(name), number=escape(number), did=did)
    return text, Keyboard(inline_keyboard=rows)


def setup(store):
    dp = Dispatcher()

    @dp.business_connection()
    async def connection_changed(connection: BusinessConnection):
        store.save_connection(connection)

    @dp.message(Command('business'))
    async def business_status(message: Message):
        if message.chat.type != 'private':
            return
        rows = store.db.execute('SELECT * FROM business_connections WHERE owner=?', (message.from_user.id,)).fetchall()
        active = any(r['enabled'] and r['can_reply'] for r in rows)
        last_error = store.setting(f'business_error:{message.from_user.id}')
        if last_error:
            await message.answer('Последняя ошибка отправки бизнес-офера:\n' + escape(last_error))
        await message.answer(
            'Бизнес-подключение активно. В разрешённом чате продавца отправьте:\n'
            '<code>/offer @продавец https://t.me/nft/PlushPepe-2687 1000</code>\n'
            'или без указания адресата (офер уходит в текущий чат):\n'
            '<code>/offer https://t.me/nft/PlushPepe-2687 1000</code>\n'
            'В конце можно добавить валюту: <code>stars</code> или <code>gram</code> (по умолчанию stars).\n'
            'Можно добавить <code>eng</code> для английской карточки.\n'
            'Команду должен отправить владелец бизнес-аккаунта.' if active else
            'Нет активного подключения с правом ответа. Включите Secretary Mode (бывш. Business Mode) в BotFather, '
            'затем подключите бота в настройках Telegram → Telegram Business → Чат-боты. '
            'Разрешите ответы в выбранных чатах.',
            disable_web_page_preview=True)

    @dp.business_message(Command('offer', 'o'))
    async def business_offer(message: Message, command: CommandObject, bot: Bot):
        if not message.business_connection_id or not message.from_user or message.sender_business_bot:
            return
        connection = await bot.get_business_connection(message.business_connection_id)
        store.save_connection(connection)
        if (not connection.is_enabled or not connection.rights or not connection.rights.can_reply
                or message.from_user.id != connection.user.id or message.chat.type != 'private'):
            return
        if not store.can_create(connection.user.id):
            store.set_setting(f'business_error:{connection.user.id}', 'Доступ к созданию оферов не активирован. Откройте /work в личке бота.')
            return
        try:
            args = command.args
            if command.command == 'o':
                if not message.chat.username:
                    raise ValueError('Для короткой команды у продавца должен быть публичный @username.')
                if len((args or '').split()) not in (2, 3):
                    raise ValueError('Формат: /o https://t.me/nft/PlushPepe-2687 20 [stars/gram] [eng]')
                args = f'@{message.chat.username} {args}'
            target, url, amount, currency, lang = parse_offer(args)
            if not connection.user.username:
                raise ValueError('Задайте публичный @username получателя подарка.')
            if target:
                if not message.chat.username or target != message.chat.username.lower():
                    raise ValueError('Адресат команды должен совпадать с @username собеседника этого чата.')
            if message.chat.id == connection.user.id:
                return
        except ValueError as exc:
            try:
                await bot.send_message(chat_id=message.chat.id, business_connection_id=connection.id,
                                       text='Автоматическое сообщение: ' + escape(str(exc)))
            except TelegramAPIError as error:
                store.set_setting(f'business_error:{connection.user.id}', error.message)
                logging.warning('Business validation reply failed: %s', error.message)
            return
        key = store.create(connection.user.id, connection.user.username, target, url, amount,
                           currency=currency, lang=lang)
        # Bind to the actual conversation partner before exposing the buttons.
        with store.db:
            store.db.execute('UPDATE offers SET seller=? WHERE id=?', (message.chat.id, key))
        text, keyboard = render(store.get(key))
        try:
            sent = await bot.send_message(chat_id=message.chat.id, business_connection_id=connection.id,
                text=text, reply_markup=keyboard,
                link_preview_options=LinkPreviewOptions(url=url, is_disabled=False,
                                                        prefer_large_media=True, show_above_text=True))
        except TelegramAPIError as exc:
            store.set_setting(f'business_error:{connection.user.id}', exc.message)
            logging.warning('Business offer could not be sent: %s', exc.message)
            return
        store.set_setting(f'business_error:{connection.user.id}', '')
        store.business_sent(key, connection.user.id, connection.id, sent.chat.id, sent.message_id)

    @dp.chosen_inline_result()
    async def chosen(result: ChosenInlineResult):
        if result.inline_message_id:
            store.mark_sent(result.result_id, result.from_user.id, result.inline_message_id)

    @dp.inline_query()
    async def inline(query: InlineQuery):
        if not store.can_create(query.from_user.id):
            await query.answer([], cache_time=0, is_personal=True,
                               button=InlineQueryResultsButton(text='Открыть бота', start_parameter='setup'))
            return
        try:
            if not query.from_user.username:
                raise ValueError('Задайте @username в настройках Telegram')
            if query.query.startswith('offer:'):
                offer = store.get(query.query.removeprefix('offer:').strip())
                if not offer or offer['buyer'] != query.from_user.id:
                    raise ValueError('Офер недоступен')
            else:
                target, url, amount, currency, lang = parse_offer(query.query)
                if target and target == query.from_user.username.lower():
                    raise ValueError('Укажите @username продавца')
                offer = store.inline_offer(query.from_user.id, query.from_user.username, target, url, amount,
                                           currency=currency, lang=lang)
        except ValueError:
            await query.answer([], cache_time=0, is_personal=True,
                               button=InlineQueryResultsButton(text='Как создать офер — инструкция', start_parameter='setup'))
            return
        text, keyboard = render(offer)
        target_label = f'@{offer["target"]}' if offer['target'] else 'текущий чат'
        await query.answer([InlineQueryResultArticle(
            id=offer['id'], title=f'{price(offer)} · {target_label}',
            description=offer['url'].rsplit('/', 1)[-1],
            input_message_content=InputTextMessageContent(
                message_text=text, parse_mode='HTML',
                link_preview_options=LinkPreviewOptions(url=offer['url'], is_disabled=False,
                                                        prefer_large_media=True, show_above_text=True)),
            reply_markup=keyboard)],
            cache_time=0, is_personal=True)

    async def show(message, offer):
        text, keyboard = render(offer)
        await message.answer(text, reply_markup=keyboard,
                             link_preview_options=LinkPreviewOptions(url=offer['url'], is_disabled=False,
                                                                     prefer_large_media=True, show_above_text=True))

    @dp.message(Command('work'))
    async def work(message: Message):
        if message.chat.type != 'private' or not message.from_user:
            return
        store.request_creator_access(message.from_user.id)
        await message.answer(
            'Создание оферов\n\nНажмите кнопку ниже — доступ активируется автоматически.\n'
            'Получатель подарка в новых оферах — вы сами (автор офера). '
            'Оплата и передача выполняются вручную.',
            reply_markup=Keyboard(inline_keyboard=[
                [Button(text='Оставить заявку inline', callback_data='work_apply')],
                [Button(text='📖 Инструкция', callback_data='show_help')]]))

    @dp.message(CommandStart())
    async def start(message: Message, command: CommandObject):
        if message.chat.type != 'private':
            return
        if command.args and command.args != 'setup':
            offer = store.get(command.args)
            if not offer or not store.allowed(offer, message.from_user.id, message.from_user.username):
                await message.answer(escape(access_error(offer, message.from_user, offer_lang(offer))))
                return
            await show(message, offer)
            return
        if command.args == 'setup':
            await message.answer(GUIDE, disable_web_page_preview=True)
            return
        await message.answer(
            '🎁 Оферы на коллекционные подарки\n\n'
            'Здесь можно получать предложения о покупке подарков в Telegram, '
            'принимать или отклонять их и отмечать этапы сделки.\n\n'
            'Отправьте /help для инструкции.',
            reply_markup=Keyboard(inline_keyboard=[[Button(text='📖 Инструкция', callback_data='show_help')]]))

    @dp.message(Command('help'))
    async def help_cmd(message: Message):
        if message.chat.type != 'private':
            return
        await message.answer(GUIDE, disable_web_page_preview=True)

    @dp.message(Command('offer'))
    async def create(message: Message, command: CommandObject, bot: Bot):
        if message.chat.type != 'private':
            return
        user = message.from_user
        if not store.can_create(user.id):
            await message.answer('Доступ к созданию оферов не активирован.')
            return
        if not user.username:
            await message.answer('Сначала задайте @username в настройках Telegram.')
            return
        try:
            target, url, amount, currency, lang = parse_offer(command.args)
            if target and target == user.username.lower():
                raise ValueError('Укажите другого пользователя.')
        except ValueError as exc:
            await message.answer(escape(str(exc)))
            return
        key = store.create(user.id, user.username, target, url, amount, currency=currency, lang=lang)
        me = await bot.get_me()
        link = f'https://t.me/{me.username}?start={key}'
        cur_name = 'Stars' if currency == 'XTR' else 'TON'
        lang_note = ' · English card' if lang == 'en' else ''
        if target:
            share_text = f'Предложение для @{target}: {amount} {cur_name} за подарок. Оплата после передачи.{lang_note}'
            created_msg = (f'Офер для @{target} создан. Вы — автор офера. Получатель подарка — вы (@{user.username}).\n'
                           f'Отправьте адресату ссылку:\n{link}\n\n'
                           'Ссылка предназначена только указанному адресату. Не меняйте свой @username до завершения сделки.')
        else:
            share_text = f'Предложение: {amount} {cur_name} за подарок. Оплата после передачи.{lang_note}'
            created_msg = (f'Офер создан (без указания адресата). Вы — автор офера. Получатель подарка — вы (@{user.username}).\n'
                           f'Отправьте ссылку любому продавцу:\n{link}\n\n'
                           'Первый, кто откроет ссылку и нажмёт «Принять», станет продавцом по этой сделке.')
        share = 'https://t.me/share/url?' + urlencode({'url': link, 'text': share_text})
        await message.answer(created_msg,
                             reply_markup=Keyboard(inline_keyboard=[
                                 [Button(text='Отправить офер в чат', switch_inline_query=f'offer:{key}')],
                                 [Button(text='Отправить ссылку', url=share)]]))

    @dp.message(Command('getemoji'))
    async def getemoji(message: Message):
        """Helper: replies to a message containing premium emoji and prints their custom_emoji_id."""
        if message.chat.type != 'private':
            return
        target = message.reply_to_message
        if not target:
            await message.answer(
                'Ответьте этой командой на сообщение с премиум-эмодзи — '
                'я пришлю их custom_emoji_id для использования в кнопках.')
            return
        entities = target.entities or []
        ids = [e.custom_emoji_id for e in entities
               if e.type == 'custom_emoji' and e.custom_emoji_id]
        if not ids:
            await message.answer('В этом сообщении нет премиум-эмодзи. Пришлите эмодзи из премиум-набора Telegram.')
            return
        lines = [f'<code>{eid}</code>' for eid in ids]
        await message.answer(
            'Найдены custom_emoji_id:\n\n' + '\n'.join(lines) +
            '\n\nСкопируй нужный ID и зашей его в кнопку Принять или Отклонить.')

    @dp.callback_query(F.data == 'show_help')
    async def show_help_cb(query: CallbackQuery):
        if not isinstance(query.message, Message) or query.message.chat.type != 'private':
            await query.answer('Откройте бота в личном чате.', show_alert=True)
            return
        await query.answer()
        await query.message.answer(GUIDE, disable_web_page_preview=True)

    @dp.callback_query(F.data.contains(':'))
    async def callback(query: CallbackQuery, bot: Bot):
        action, key = query.data.split(':', 1)
        offer = store.get(key)
        is_inline = bool(query.inline_message_id)
        lang = offer_lang(offer)
        t = T[lang]
        if not is_inline and (not isinstance(query.message, Message) or query.message.chat.type != 'private'):
            await query.answer(t['alert_private_only'], show_alert=True)
            return
        if not store.allowed(offer, query.from_user.id, query.from_user.username):
            await query.answer(access_error(offer, query.from_user, lang), show_alert=True)
            return
        business_id = query.message.business_connection_id if isinstance(query.message, Message) else None
        if business_id:
            connection = await bot.get_business_connection(business_id)
            if not connection.is_enabled or connection.user.id != offer['buyer']:
                await query.answer(t['alert_biz_unavailable'], show_alert=True)
                return
        async def display(text, keyboard):
            if business_id:
                try:
                    await bot.edit_message_text(business_connection_id=business_id,
                        chat_id=query.message.chat.id, message_id=query.message.message_id,
                        text=text, parse_mode='HTML', reply_markup=keyboard,
                        link_preview_options=LinkPreviewOptions(url=offer['url'], is_disabled=False,
                                                                prefer_large_media=True, show_above_text=True))
                except TelegramBadRequest as exc:
                    if 'message is not modified' not in str(exc).lower():
                        raise
                return
            if is_inline:
                try:
                    await bot.edit_message_text(inline_message_id=query.inline_message_id,
                                                text=text, parse_mode='HTML', reply_markup=keyboard,
                                                link_preview_options=LinkPreviewOptions(
                                                    url=offer['url'], is_disabled=False,
                                                    prefer_large_media=True, show_above_text=True))
                except TelegramBadRequest as exc:
                    error = str(exc).lower()
                    if 'there is no text in the message to edit' in error:
                        await bot.edit_message_caption(inline_message_id=query.inline_message_id,
                                                       caption=text, parse_mode='HTML', reply_markup=keyboard)
                    elif 'message is not modified' not in error:
                        raise
            else:
                await query.message.answer(text, reply_markup=keyboard,
                                           link_preview_options=LinkPreviewOptions(
                                               url=offer['url'], is_disabled=False,
                                               prefer_large_media=True, show_above_text=True))

        if action in {'transfer', 'help'}:
            if offer['state'] != 'accepted':
                await query.answer(t['alert_not_accepted'], show_alert=True)
                return
            await query.answer()
            await display(*render(offer))
            return
        if action == 'paid' and offer['state'] == 'pending':
            await query.answer()
            await display(t['alert_confirm_paid'],
                Keyboard(inline_keyboard=[[Button(text=t['btn_confirm_yes'], callback_data=f'confirm_paid:{key}')],
                                         [Button(text=t['btn_back'], callback_data=f'view:{key}')]]))
            return
        if action == 'view':
            await query.answer()
            await display(*render(offer))
            return
        if action == 'confirm_paid':
            action = 'paid'
        if not store.transition(key, query.from_user.id, query.from_user.username, action):
            await query.answer(t['alert_status_changed'], show_alert=True)
            return
        if action == 'accept':
            name, number = gift_info(offer)
            await query.answer(
                t['alert_accept'].format(name=name, number=number, price=price(offer)),
                show_alert=True)
        else:
            await query.answer()
        await display(*render(store.get(key)))

    @dp.callback_query(F.data == 'work_apply')
    async def apply_work(query: CallbackQuery):
        if (not isinstance(query.message, Message) or query.message.chat.type != 'private'
                or query.message.chat.id != query.from_user.id):
            await query.answer('Откройте команду /work в личном чате с ботом.', show_alert=True)
            return
        if not store.activate_creator(query.from_user.id):
            await query.answer('Сначала отправьте /work в личном чате с ботом.', show_alert=True)
            return
        await query.answer('Доступ открыт')
        await query.message.answer(
            '✅ Доступ к созданию оферов открыт.\n\n'
            'Нажмите кнопку и выберите чат продавца. В запросе укажите:\n'
            '<code>@продавец https://t.me/nft/PlushPepe-2687 20</code>\n'
            'или без @продавца (офер уходит в текущий чат):\n'
            '<code>https://t.me/nft/PlushPepe-2687 20</code>\n\n'
            'В конце можно добавить <code>stars</code> или <code>gram</code> (по умолчанию stars).\n'
            'Добавьте <code>eng</code> для карточки на английском.\n'
            'Получатель подарка — автор офера.',
            reply_markup=Keyboard(inline_keyboard=[
                [Button(text='Создать офер inline', switch_inline_query='')],
                [Button(text='📖 Инструкция', callback_data='show_help')]]))

    return dp


async def update_timers(bot, store):
    while True:
        for row in store.db.execute('SELECT * FROM business_messages').fetchall():
            offer = store.get(row['offer_id'])
            if not offer or offer['state'] != 'new':
                continue
            connection = store.db.execute('SELECT * FROM business_connections WHERE id=?', (row['connection'],)).fetchone()
            if not connection or not connection['enabled'] or not connection['can_reply']:
                continue
            text, keyboard = render(offer)
            try:
                await bot.edit_message_text(business_connection_id=row['connection'], chat_id=row['chat'],
                    message_id=row['message'], text=text, parse_mode='HTML', reply_markup=keyboard,
                    link_preview_options=LinkPreviewOptions(url=offer['url'], is_disabled=False,
                                                            prefer_large_media=True, show_above_text=True))
            except TelegramRetryAfter as exc:
                await asyncio.sleep(exc.retry_after)
            except TelegramAPIError:
                pass
            if offer['expires'] and time.time() >= offer['expires']:
                with store.db:
                    store.db.execute('DELETE FROM business_messages WHERE connection=? AND chat=? AND message=?',
                                     (row['connection'], row['chat'], row['message']))
            await asyncio.sleep(0.05)
        for row in store.db.execute('SELECT message_id, offer_id FROM inline_messages').fetchall():
            offer = store.get(row['offer_id'])
            if not offer or offer['state'] != 'new':
                continue
            text, keyboard = render(offer)
            try:
                await bot.edit_message_text(inline_message_id=row['message_id'], text=text,
                    parse_mode='HTML', reply_markup=keyboard,
                    link_preview_options=LinkPreviewOptions(url=offer['url'], is_disabled=False,
                                                            prefer_large_media=True, show_above_text=True))
            except TelegramRetryAfter as exc:
                await asyncio.sleep(exc.retry_after)
            except TelegramBadRequest as exc:
                if 'message is not modified' not in str(exc).lower():
                    with store.db:
                        store.db.execute('DELETE FROM inline_messages WHERE message_id=?', (row['message_id'],))
            except TelegramAPIError:
                logging.warning('Timer update temporarily failed')
            else:
                if offer['expires'] and time.time() >= offer['expires']:
                    with store.db:
                        store.db.execute('DELETE FROM inline_messages WHERE message_id=?', (row['message_id'],))
            await asyncio.sleep(0.05)
        await asyncio.sleep(30)


async def main():
    token = BOT_TOKEN.strip()
    if not token or 'ВСТАВЬ' in token:
        raise SystemExit(
            'Токен бота не задан. Откройте main.py и впишите свой токен от @BotFather '
            'в переменную BOT_TOKEN в верхней части файла.'
        )
    store = Store(ROOT / 'offers.sqlite3')
    async with Bot(token, default=DefaultBotProperties(parse_mode='HTML')) as bot:
        timer = asyncio.create_task(update_timers(bot, store))
        try:
            await setup(store).start_polling(bot)
        finally:
            timer.cancel()
            with suppress(asyncio.CancelledError):
                await timer


if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(main())
