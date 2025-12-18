import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)
from database import Database
from config import BOT_TOKEN, DATABASE_FILE
from languages import get_text, get_available_languages
import re
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = Database(DATABASE_FILE)

# ADMIN USER IDS - Add your Telegram user ID here
ADMIN_USER_IDS = [6653573130]  # Replace with your actual user ID

# Helper function to get user's language
def get_user_lang(user_id):
    """Get user's language preference"""
    return db.get_user_language(user_id)

# Language selection keyboard
def get_language_keyboard():
    """Create language selection keyboard"""
    languages = get_available_languages()
    keyboard = []
    
    row = []
    for code, flag, name in languages:
        row.append(InlineKeyboardButton(f"{flag} {name}", callback_data=f"lang_{code}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard)

# Keyboard layouts
def get_home_keyboard(lang='en'):
    """Main menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(get_text(lang, 'menu_my_notes'), callback_data="menu_notes"),
            InlineKeyboardButton(get_text(lang, 'menu_search'), callback_data="menu_search")
        ],
        [
            InlineKeyboardButton(get_text(lang, 'menu_pinned'), callback_data="menu_pinned"),
            InlineKeyboardButton(get_text(lang, 'menu_stats'), callback_data="menu_stats")
        ],
        [
            InlineKeyboardButton(get_text(lang, 'menu_random'), callback_data="menu_random"),
            InlineKeyboardButton(get_text(lang, 'menu_help'), callback_data="menu_help")
        ],
        [
            InlineKeyboardButton(get_text(lang, 'menu_settings'), callback_data="menu_settings")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_note_actions_keyboard(note_id, is_pinned=False, lang='en'):
    """Actions for a specific note"""
    pin_text = "📌 Unpin" if is_pinned else "📌 Pin"
    keyboard = [
        [
            InlineKeyboardButton("🏷️ Add Tags", callback_data=f"tag_{note_id}"),
            InlineKeyboardButton(pin_text, callback_data=f"pin_{note_id}")
        ],
        [
            InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_{note_id}"),
            InlineKeyboardButton(get_text(lang, 'menu_home'), callback_data="menu_home")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard(lang='en'):
    """Simple back button"""
    keyboard = [[InlineKeyboardButton(get_text(lang, 'menu_home'), callback_data="menu_home")]]
    return InlineKeyboardMarkup(keyboard)

def get_search_keyboard(user_id, lang='en'):
    """Quick search filters"""
    tags = db.get_popular_tags(user_id, limit=6)
    keyboard = []
    
    tag_row = []
    for i, tag in enumerate(tags):
        tag_row.append(InlineKeyboardButton(f"#{tag}", callback_data=f"search_tag_{tag}"))
        if (i + 1) % 3 == 0:
            keyboard.append(tag_row)
            tag_row = []
    if tag_row:
        keyboard.append(tag_row)
    
    keyboard.append([
        InlineKeyboardButton(get_text(lang, 'btn_this_week'), callback_data="search_week"),
        InlineKeyboardButton(get_text(lang, 'menu_pinned'), callback_data="menu_pinned")
    ])
    keyboard.append([InlineKeyboardButton(get_text(lang, 'menu_home'), callback_data="menu_home")])
    
    return InlineKeyboardMarkup(keyboard)

def get_settings_keyboard(lang='en'):
    """Settings menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(get_text(lang, 'change_language'), callback_data="settings_language")
        ],
        [
            InlineKeyboardButton(get_text(lang, 'menu_home'), callback_data="menu_home")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message with language selection"""
    user = update.effective_user
    
    user_lang = db.get_user_language(user.id)
    
    if not user_lang or user_lang == 'en':
        db.ensure_user(user.id, user.username, user.first_name, 'en')
        
        await update.message.reply_text(
            f"👋 Welcome {user.first_name}!\n\n🌐 Please choose your language:",
            reply_markup=get_language_keyboard()
        )
    else:
        await show_welcome(update.message, user, user_lang)
    
    # Log activity
    db.log_user_activity(user.id, 'bot_started')

async def show_welcome(message, user, lang):
    """Show welcome message after language is set"""
    welcome_text = (
        f"👋 {user.first_name}!\n\n"
        f"{get_text(lang, 'welcome_title')}\n\n"
        f"{get_text(lang, 'welcome_text')}"
    )
    
    await message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=get_home_keyboard(lang)
    )

async def analytics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show analytics (admin only)"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("⛔ Access denied! You are not authorized to view analytics.")
        return
    
    # Log admin access
    db.log_user_activity(user_id, 'admin_analytics_viewed')
    
    # Generate stats
    total_users = db.get_total_users()
    active_7d = db.get_active_users(7)
    active_30d = db.get_active_users(30)
    total_notes = db.get_total_notes_all_users()
    new_users_today = db.get_new_users_today()
    notes_today = db.get_notes_created_today()
    languages = db.get_language_distribution()
    note_types = db.get_notes_by_type_stats()
    top_users = db.get_top_users(5)
    popular_tags = db.get_popular_tags_global(10)
    
    # Calculate percentages
    activity_rate_7d = (active_7d / total_users * 100) if total_users > 0 else 0
    activity_rate_30d = (active_30d / total_users * 100) if total_users > 0 else 0
    avg_notes_per_user = (total_notes / total_users) if total_users > 0 else 0
    
    text = (
        "📊 *BOT ANALYTICS DASHBOARD*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        "👥 *USER STATISTICS*\n"
        f"├ Total Users: `{total_users}`\n"
        f"├ New Today: `{new_users_today}`\n"
        f"├ Active (7d): `{active_7d}` ({activity_rate_7d:.1f}%)\n"
        f"└ Active (30d): `{active_30d}` ({activity_rate_30d:.1f}%)\n\n"
        
        "📝 *NOTE STATISTICS*\n"
        f"├ Total Notes: `{total_notes}`\n"
        f"├ Created Today: `{notes_today}`\n"
        f"└ Avg per User: `{avg_notes_per_user:.1f}`\n\n"
    )
    
    # Language distribution
    text += "🌐 *LANGUAGE DISTRIBUTION*\n"
    lang_names = {
        'en': '🇺🇸 English',
        'es': '🇪🇸 Español',
        'ar': '🇸🇦 العربية',
        'ru': '🇷🇺 Русский',
        'tr': '🇹🇷 Türkçe',
        'uz': '🇺🇿 O\'zbekcha'
    }
    for lang, count in languages.items():
        percentage = (count / total_users * 100) if total_users > 0 else 0
        lang_display = lang_names.get(lang, lang)
        text += f"├ {lang_display}: `{count}` ({percentage:.1f}%)\n"
    text += "\n"
    
    # Note types
    if note_types:
        text += "📊 *CONTENT TYPES*\n"
        type_icons = {
            'text': '📄',
            'photo': '📷',
            'video': '🎥',
            'document': '📁',
            'voice': '🎤',
            'audio': '🎵'
        }
        for note_type, count in note_types.items():
            percentage = (count / total_notes * 100) if total_notes > 0 else 0
            icon = type_icons.get(note_type, '📝')
            text += f"├ {icon} {note_type}: `{count}` ({percentage:.1f}%)\n"
        text += "\n"
    
    # Top users
    if top_users:
        text += "🏆 *TOP 5 USERS*\n"
        for i, (uid, first_name, username, note_count) in enumerate(top_users, 1):
            username_display = f"@{username}" if username else f"ID:{uid}"
            text += f"{i}. {first_name} ({username_display}): `{note_count}` notes\n"
        text += "\n"
    
    # Popular tags
    if popular_tags:
        text += "🏷️ *TOP 10 TAGS*\n"
        for i, (tag, count) in enumerate(popular_tags, 1):
            text += f"{i}. #{tag}: `{count}` uses\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    await update.message.reply_text(text, parse_mode='Markdown')

# Message handler - save notes
async def save_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save any forwarded or sent message"""
    user_id = update.effective_user.id
    message = update.message
    lang = get_user_lang(user_id)
    
    content = ""
    message_type = "text"
    file_id = None
    
    if message.text:
        content = message.text
        message_type = "text"
    elif message.photo:
        content = message.caption or "📷 Photo"
        message_type = "photo"
        file_id = message.photo[-1].file_id
    elif message.video:
        content = message.caption or "🎥 Video"
        message_type = "video"
        file_id = message.video.file_id
    elif message.document:
        content = message.caption or f"📄 {message.document.file_name}"
        message_type = "document"
        file_id = message.document.file_id
    elif message.voice:
        content = "🎤 Voice message"
        message_type = "voice"
        file_id = message.voice.file_id
    elif message.audio:
        content = message.caption or "🎵 Audio"
        message_type = "audio"
        file_id = message.audio.file_id
    
    source_chat_id = None
    source_chat_title = None
    if message.forward_from_chat:
        source_chat_id = message.forward_from_chat.id
        source_chat_title = message.forward_from_chat.title
    
    hashtags = re.findall(r'#(\w+)', content)
    
    note_id = db.save_note(
        user_id=user_id,
        content=content,
        message_type=message_type,
        file_id=file_id,
        source_chat_id=source_chat_id,
        source_chat_title=source_chat_title
    )
    
    for tag in hashtags:
        db.add_tag(note_id, tag.lower())
    
    # Log activity
    db.log_user_activity(user_id, 'note_created', f'type:{message_type}')
    
    response_text = get_text(lang, 'note_saved', note_id)
    if hashtags:
        tag_text = ', '.join(['#' + t for t in hashtags])
        response_text += get_text(lang, 'auto_tagged', tag_text)
    
    await message.reply_text(
        response_text,
        reply_markup=get_note_actions_keyboard(note_id, lang=lang)
    )

async def view_note_original(query, user_id, note_id, context):
    """Resend the original message"""
    lang = get_user_lang(user_id)
    note = db.get_note(note_id, user_id)
    
    if not note:
        await query.answer("Note not found!")
        return
    
    content, created_at, pinned, tags, message_type, file_id = note
    
    chat_id = query.message.chat_id
    
    if isinstance(created_at, str):
        try:
            created_at = datetime.fromisoformat(created_at)
        except:
            created_at = datetime.now()
    
    tag_text = " ".join([f"#{t}" for t in tags]) if tags else ""
    caption_text = (
        f"📌 *Note #{note_id}*\n"
        f"📅 {created_at.strftime('%b %d, %Y')}\n"
    )
    if tag_text:
        caption_text += f"{tag_text}\n"
    caption_text += f"\n{content}"
    
    # Log activity
    db.log_user_activity(user_id, 'note_viewed', f'note_id:{note_id}')
    
    try:
        if message_type == "photo" and file_id:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=file_id,
                caption=caption_text,
                parse_mode='Markdown'
            )
        elif message_type == "video" and file_id:
            await context.bot.send_video(
                chat_id=chat_id,
                video=file_id,
                caption=caption_text,
                parse_mode='Markdown'
            )
        elif message_type == "document" and file_id:
            await context.bot.send_document(
                chat_id=chat_id,
                document=file_id,
                caption=caption_text,
                parse_mode='Markdown'
            )
        elif message_type == "voice" and file_id:
            await context.bot.send_voice(
                chat_id=chat_id,
                voice=file_id
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text=caption_text,
                parse_mode='Markdown'
            )
        elif message_type == "audio" and file_id:
            await context.bot.send_audio(
                chat_id=chat_id,
                audio=file_id,
                caption=caption_text,
                parse_mode='Markdown'
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=caption_text,
                parse_mode='Markdown'
            )
        
        await query.answer("✅ Message sent below!")
    except Exception as e:
        logger.error(f"Error sending note: {e}")
        await query.answer("❌ Error sending message!")

# Callback query handler
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all button clicks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    lang = get_user_lang(user_id)
    
    # Language selection
    if data.startswith("lang_"):
        new_lang = data.split("_")[1]
        db.set_user_language(user_id, new_lang)
        db.log_user_activity(user_id, 'language_changed', f'to:{new_lang}')
        
        await query.edit_message_text(
            get_text(new_lang, 'language_selected')
        )
        
        user = query.from_user
        await show_welcome(query.message, user, new_lang)
        return
    
    # Menu navigation
    if data == "menu_home":
        db.log_user_activity(user_id, 'menu_home')
        await show_home(query, lang)
    
    elif data == "menu_notes":
        db.log_user_activity(user_id, 'view_notes')
        await show_notes(query, user_id, page=0, lang=lang)
    
    elif data == "menu_search":
        db.log_user_activity(user_id, 'search_initiated')
        await show_search_menu(query, user_id, context, lang)
    
    elif data == "menu_pinned":
        db.log_user_activity(user_id, 'view_pinned')
        await show_pinned_notes(query, user_id, lang)
    
    elif data == "menu_stats":
        db.log_user_activity(user_id, 'view_stats')
        await show_stats(query, user_id, lang)
    
    elif data == "menu_random":
        db.log_user_activity(user_id, 'random_note')
        await show_random_note(query, user_id, lang)
    
    elif data == "menu_help":
        db.log_user_activity(user_id, 'view_help')
        await show_help(query, lang)
    
    elif data == "menu_settings":
        db.log_user_activity(user_id, 'view_settings')
        await show_settings(query, lang)
    
    elif data == "settings_language":
        await query.edit_message_text(
            get_text(lang, 'choose_language'),
            reply_markup=get_language_keyboard()
        )
    
    # Note actions
    elif data.startswith("view_"):
        note_id = int(data.split("_")[1])
        await view_note_original(query, user_id, note_id, context)
    
    elif data.startswith("tag_"):
        note_id = int(data.split("_")[1])
        context.user_data['awaiting_tags'] = note_id
        await query.edit_message_text(
            get_text(lang, 'send_tags'),
            reply_markup=get_back_keyboard(lang)
        )
    
    elif data.startswith("pin_"):
        note_id = int(data.split("_")[1])
        db.toggle_pin(note_id)
        db.log_user_activity(user_id, 'note_pinned', f'note_id:{note_id}')
        await query.answer(get_text(lang, 'pin_updated'))
        await show_notes(query, user_id, page=0, lang=lang)
    
    elif data.startswith("delete_"):
        note_id = int(data.split("_")[1])
        
        keyboard = [
            [
                InlineKeyboardButton(get_text(lang, 'btn_yes_delete'), callback_data=f"confirm_delete_{note_id}"),
                InlineKeyboardButton(get_text(lang, 'btn_cancel'), callback_data="menu_notes")
            ]
        ]
        
        await query.edit_message_text(
            get_text(lang, 'delete_confirm', note_id),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data.startswith("confirm_delete_"):
        note_id = int(data.split("_")[2])
        db.delete_note(note_id)
        db.log_user_activity(user_id, 'note_deleted', f'note_id:{note_id}')
        await query.answer(get_text(lang, 'note_deleted'))
        await show_notes(query, user_id, page=0, lang=lang)
    
    # Pagination
    elif data.startswith("notes_page_"):
        page = int(data.split("_")[2])
        await show_notes(query, user_id, page, lang)
    
    # Search
    elif data.startswith("search_tag_"):
        tag = data.split("_", 2)[2]
        db.log_user_activity(user_id, 'search_by_tag', f'tag:{tag}')
        await search_by_tag(query, user_id, tag, lang)
    
    elif data == "search_week":
        db.log_user_activity(user_id, 'search_week')
        await search_this_week(query, user_id, lang)
    
    elif data == "noop":
        pass

# Menu display functions
async def show_home(query, lang='en'):
    """Show main menu"""
    await query.edit_message_text(
        f"{get_text(lang, 'welcome_title')}\n\n{get_text(lang, 'menu_home')}:",
        parse_mode='Markdown',
        reply_markup=get_home_keyboard(lang)
    )

async def show_settings(query, lang='en'):
    """Show settings menu"""
    await query.edit_message_text(
        get_text(lang, 'settings_title'),
        parse_mode='Markdown',
        reply_markup=get_settings_keyboard(lang)
    )

async def show_notes(query, user_id, page=0, per_page=5, lang='en'):
    """Show recent notes with pagination"""
    offset = page * per_page
    notes = db.get_recent_notes(user_id, limit=per_page, offset=offset)
    total_count = db.get_note_count(user_id)
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    
    if not notes:
        await query.edit_message_text(
            get_text(lang, 'no_notes'),
            reply_markup=get_back_keyboard(lang)
        )
        return
    
    text = get_text(lang, 'recent_notes', page + 1, total_pages) + "\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for i, note in enumerate(notes):
        note_id, content, created_at, pinned, message_type, file_id, tags = note
        
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except:
                created_at = datetime.now()
        
        display_content = content[:100] + "..." if len(content) > 100 else content
        
        media_icons = {
            "photo": "📷",
            "video": "🎥",
            "document": "📄",
            "voice": "🎤",
            "audio": "🎵"
        }
        media_icon = media_icons.get(message_type, "")
        
        pin_emoji = "📌 " if pinned else ""
        tag_text = " ".join([f"#{t}" for t in tags]) if tags else ""
        
        text += (
            f"{pin_emoji}{media_icon} *Note #{note_id}*\n"
            f"{display_content}\n"
        )
        
        if tag_text:
            text += f"{tag_text}\n"
        
        text += f"📅 {created_at.strftime('%b %d, %Y')}\n"
        
        if i < len(notes) - 1:
            text += "\n─────────────────\n\n"
        else:
            text += "\n"
    
    keyboard = []
    
    for note in notes[:3]:
        note_id = note[0]
        pinned = note[3]
        message_type = note[4]
        pin_icon = "📍" if pinned else "📌"
        
        if message_type != "text":
            keyboard.append([
                InlineKeyboardButton(f"👁️ View #{note_id}", callback_data=f"view_{note_id}"),
                InlineKeyboardButton(f"🏷️ #{note_id}", callback_data=f"tag_{note_id}"),
                InlineKeyboardButton(f"🗑️ #{note_id}", callback_data=f"delete_{note_id}")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton(f"🏷️ Tag #{note_id}", callback_data=f"tag_{note_id}"),
                InlineKeyboardButton(f"{pin_icon} #{note_id}", callback_data=f"pin_{note_id}"),
                InlineKeyboardButton(f"🗑️ #{note_id}", callback_data=f"delete_{note_id}")
            ])
    
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(get_text(lang, 'btn_previous'), callback_data=f"notes_page_{page-1}"))
    
    nav_row.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
    
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(get_text(lang, 'btn_next'), callback_data=f"notes_page_{page+1}"))
    
    keyboard.append(nav_row)
    keyboard.append([InlineKeyboardButton(get_text(lang, 'menu_home'), callback_data="menu_home")])
    
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_search_menu(query, user_id, context, lang='en'):
    """Show search options"""
    context.user_data['awaiting_search'] = True
    
    await query.edit_message_text(
        get_text(lang, 'search_prompt'),
        parse_mode='Markdown',
        reply_markup=get_search_keyboard(user_id, lang)
    )

async def show_pinned_notes(query, user_id, lang='en'):
    """Show all pinned notes"""
    notes = db.get_pinned_notes(user_id)
    
    if not notes:
        await query.edit_message_text(
            get_text(lang, 'no_pinned'),
            reply_markup=get_back_keyboard(lang)
        )
        return
    
    text = get_text(lang, 'pinned_notes') + "\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for i, note in enumerate(notes):
        note_id, content, created_at, tags = note
        display_content = content[:80] + "..." if len(content) > 80 else content
        tag_text = " ".join([f"#{t}" for t in tags]) if tags else ""
        
        text += f"*Note #{note_id}*\n{display_content}\n"
        
        if tag_text:
            text += f"{tag_text}\n"
        
        if i < len(notes) - 1:
            text += "\n─────────────────\n\n"
        else:
            text += "\n"
    
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=get_back_keyboard(lang)
    )

async def show_stats(query, user_id, lang='en'):
    """Show user statistics"""
    stats = db.get_user_stats(user_id)
    
    text = (
        f"{get_text(lang, 'statistics')}\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{get_text(lang, 'total_notes', stats['total_notes'])}\n"
        f"{get_text(lang, 'pinned_count', stats['pinned_count'])}\n"
        f"{get_text(lang, 'unique_tags', stats['unique_tags'])}\n"
        f"{get_text(lang, 'first_note', stats['first_note_date'])}\n\n"
    )
    
    if stats['top_tags']:
        text += f"{get_text(lang, 'most_used_tags')}\n"
        for tag, count in stats['top_tags']:
            text += f"#{tag}: {count}\n"
    else:
        text += get_text(lang, 'no_tags_yet')
    
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=get_back_keyboard(lang)
    )

async def show_random_note(query, user_id, lang='en'):
    """Show a random note"""
    note = db.get_random_note(user_id)
    
    if not note:
        await query.answer("No notes found!")
        return
    
    note_id, content, tags = note
    tag_text = " ".join([f"#{t}" for t in tags]) if tags else ""
    
    text = (
        f"{get_text(lang, 'random_note', note_id)}\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{content}\n\n"
    )
    
    if tag_text:
        text += f"{tag_text}"
    
    keyboard = [
        [InlineKeyboardButton(get_text(lang, 'btn_another'), callback_data="menu_random")],
        [InlineKeyboardButton(get_text(lang, 'menu_home'), callback_data="menu_home")]
    ]
    
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_help(query, lang='en'):
    """Show help message"""
    await query.edit_message_text(
        f"{get_text(lang, 'help_title')}\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{get_text(lang, 'help_text')}",
        parse_mode='Markdown',
        reply_markup=get_back_keyboard(lang)
    )

async def search_by_tag(query, user_id, tag, lang='en'):
    """Search notes by tag"""
    notes = db.search_by_tag(user_id, tag)
    
    if not notes:
        await query.answer(get_text(lang, 'no_notes_tag', tag))
        return
    
    text = get_text(lang, 'notes_tagged', tag) + "\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for i, note in enumerate(notes[:10]):
        note_id, content, created_at = note
        display_content = content[:80] + "..." if len(content) > 80 else content
        text += f"*Note #{note_id}*\n{display_content}\n"
        
        if i < min(len(notes), 10) - 1:
            text += "\n─────────────────\n\n"
        else:
            text += "\n"
    
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=get_back_keyboard(lang)
    )

async def search_this_week(query, user_id, lang='en'):
    """Search notes from this week"""
    notes = db.search_this_week(user_id)
    
    if not notes:
        await query.answer(get_text(lang, 'no_notes_week'))
        return
    
    text = get_text(lang, 'week_notes') + "\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for i, note in enumerate(notes[:10]):
        note_id, content, created_at = note
        display_content = content[:80] + "..." if len(content) > 80 else content
        text += f"*Note #{note_id}*\n{display_content}\n"
        
        if i < min(len(notes), 10) - 1:
            text += "\n─────────────────\n\n"
        else:
            text += "\n"
    
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=get_back_keyboard(lang)
    )

# Text handler
async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text input for search or tagging"""
    user_id = update.effective_user.id
    text = update.message.text
    lang = get_user_lang(user_id)
    
    if 'awaiting_tags' in context.user_data:
        note_id = context.user_data['awaiting_tags']
        tags = re.split(r'[,\s]+', text.strip().lower())
        
        for tag in tags:
            if tag:
                db.add_tag(note_id, tag)
        
        db.log_user_activity(user_id, 'tags_added', f'note_id:{note_id}')
        del context.user_data['awaiting_tags']
        
        await update.message.reply_text(
            get_text(lang, 'tags_added', note_id),
            reply_markup=get_home_keyboard(lang)
        )
        return
    
    if context.user_data.get('awaiting_search'):
        results = db.search_notes(user_id, text)
        
        db.log_user_activity(user_id, 'search_performed', f'query:{text}')
        
        if not results:
            await update.message.reply_text(
                get_text(lang, 'no_results', text),
                reply_markup=get_back_keyboard(lang)
            )
            return
        
        result_text = get_text(lang, 'search_results', text) + "\n"
        result_text += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for i, note in enumerate(results[:10]):
            note_id, content, created_at = note
            display_content = content[:80] + "..." if len(content) > 80 else content
            result_text += f"*Note #{note_id}*\n{display_content}\n"
            
            if i < min(len(results), 10) - 1:
                result_text += "\n─────────────────\n\n"
            else:
                result_text += "\n"
        
        await update.message.reply_text(
            result_text,
            parse_mode='Markdown',
            reply_markup=get_back_keyboard(lang)
        )
        
        context.user_data['awaiting_search'] = False
        return
    
    await save_message(update, context)

# Main function
def main():
    """Start the bot"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("analytics", analytics_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_text_input
    ))
    application.add_handler(MessageHandler(
        filters.PHOTO | filters.VIDEO | filters.Document.ALL | 
        filters.VOICE | filters.AUDIO,
        save_message
    ))
    
    logger.info("Bot started with multi-language support and analytics!")
    application.run_polling()

if __name__ == '__main__':
    main()