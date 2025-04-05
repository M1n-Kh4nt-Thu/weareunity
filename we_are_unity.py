import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters
)
import sqlite3
from datetime import datetime

# Database Setup
DB_FILE = 'emergency_help.db'

# Bot Configuration
TOKEN = "8021498754:AAGAued_mqGUH_5lp0r_0MXWHpi98CK5kNQ"
ADMIN_IDS = [7394782364]  # Replace with your Telegram User ID

# Conversation States
REGION, NEW_REGION, HELP_TYPE, LOCATION, DESCRIPTION, PHONE, FB_LINK, CONFIRM = range(8)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def init_db():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Drop existing tables if they exist (for development)
    c.execute('DROP TABLE IF EXISTS volunteers')
    c.execute('DROP TABLE IF EXISTS help_requests')
    c.execute('DROP TABLE IF EXISTS regions')
    c.execute('DROP TABLE IF EXISTS user_settings')
    
    # Create tables with correct schema
    c.execute('''CREATE TABLE IF NOT EXISTS regions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL)''')

    c.execute('''CREATE TABLE IF NOT EXISTS help_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                region_id INTEGER NOT NULL,
                help_type TEXT NOT NULL,
                location TEXT NOT NULL,
                description TEXT NOT NULL,
                phone TEXT,
                fb_link TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (region_id) REFERENCES regions(id))''')

    c.execute('''CREATE TABLE IF NOT EXISTS volunteers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                region_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                help_type TEXT NOT NULL,
                location TEXT NOT NULL,
                phone TEXT,
                fb_link TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (region_id) REFERENCES regions(id))''')

    # NEW: Notification settings table
    c.execute('''CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                notifications_enabled BOOLEAN DEFAULT 1)''')

    # Insert default regions
    default_regions = ['စစ်ကိုင်း', 'မန္တလေး', 'ရှမ်း', 'နေပြည်တော်']
    for region in default_regions:
        try:
            c.execute('INSERT OR IGNORE INTO regions (name) VALUES (?)', (region,))
        except sqlite3.IntegrityError:
            pass
    
    conn.commit()
    conn.close()

def get_db_connection():
    """Get a database connection"""
    return sqlite3.connect(DB_FILE)

# NEW: Notification functions
def is_notification_enabled(user_id):
    """Check if notifications are enabled for user"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT notifications_enabled FROM user_settings WHERE user_id=?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 1  # Default to enabled

async def toggle_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle notification setting"""
    user_id = update.effective_user.id
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('SELECT notifications_enabled FROM user_settings WHERE user_id=?', (user_id,))
    result = c.fetchone()
    
    new_status = 0 if (result and result[0]) else 1
    c.execute('''INSERT OR REPLACE INTO user_settings 
                (user_id, notifications_enabled) VALUES (?,?)''', (user_id, new_status))
    conn.commit()
    conn.close()
    
    status_text = "ဖွင့်ထားပါပြီ 🔔" if new_status else "ပိတ်ထားပါပြီ 🔕"
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        f"အသိပေးချက်များ: {status_text}\n/start ကိုနှိပ်ပြန်စပါ")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    context.user_data.clear()
    
    keyboard = [
        [InlineKeyboardButton("🆘 အကူအညီတောင်းမယ်", callback_data='need_help'),
         InlineKeyboardButton("🤝 အကူအညီပေးမယ်", callback_data='give_help')],
        [InlineKeyboardButton("🔔 အသိပေးချက်များ ပိတ်/ဖွင့်", callback_data='toggle_noti')]
    ]
    
    if update.message:
        await update.message.reply_text(
            "ကျေးဇူးပြု၍ ရွေးချယ်ပါ:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            "ကျေးဇူးပြု၍ ရွေးချယ်ပါ:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ✨ ဒီနေရာမှာ cancel() function ကိုသီးသန့်ရေးပါ
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """အသုံးပြုသူက conversation ကိုဖျက်သိမ်းတဲ့အခါ အလိုအလျောက်ခေါ်တယ်"""
    user = update.message.from_user
    logger.info(f"User {user.first_name} canceled the conversation.")
    await update.message.reply_text(
        "❌ လုပ်ဆောင်မှုကိုဖျက်သိမ်းလိုက်ပါပြီ။ /start နဲ့ပြန်စပါ။",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()  # သိမ်းထားတဲ့ data တွေအားလုံးကိုဖျက်မယ်
    return ConversationHandler.END

async def handle_main_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the main menu selection."""
    query = update.callback_query
    await query.answer()
    # ... ကျန်တဲ့ကုဒ် ...
async def handle_main_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the main menu selection."""
    query = update.callback_query
    await query.answer()
    
    if query.data in ['need_help', 'give_help']:
        context.user_data['is_volunteer'] = (query.data == 'give_help')
        return await show_region_selection(update, context)
    elif query.data == 'toggle_noti':
        return await toggle_notifications(update, context)
    elif query.data == 'notifications':
        await query.edit_message_text("🔔 အသိပေးချက်စနစ်ကို ဖွင့်ထားပါပြီ")
        return ConversationHandler.END


async def show_region_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show region selection to user."""
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute('SELECT * FROM regions')
        regions = c.fetchall()
        
        buttons = []
        for region in regions:
            buttons.append([InlineKeyboardButton(region[1], callback_data=f'region_{region[0]}')])
        buttons.append([InlineKeyboardButton("➕ တိုင်းဒေသအသစ်ထည့်မည်", callback_data='new_region')])
        
        query = update.callback_query
        await query.edit_message_text(
            "ကျေးဇူးပြု၍ တိုင်းဒေသကိုရွေးချယ်ပါ:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return REGION
    except Exception as e:
        logger.error(f"Database error: {e}")
        await update.callback_query.edit_message_text("ဒေတာဘေ့စ်အမှားတစ်ခုဖြစ်နေပါသည်။ /start ဖြင့်ပြန်စပါ")
    finally:
        conn.close()
    return ConversationHandler.END

async def handle_region_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the region selection."""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'new_region':
        await query.edit_message_text("ကျေးဇူးပြု၍ တိုင်းဒေသအသစ်အမည်ထည့်ပါ:")
        return NEW_REGION
    
    if query.data.startswith('region_'):
        context.user_data['region_id'] = int(query.data.split('_')[1])
        await query.edit_message_text("ကျေးဇူးပြု၍ အကူအညီအမျိုးအစားရွေးပါ (ဥပမာ - ဆေးဝါး, အစားအစာ, သယ်ယူပို့ဆောင်ရေး):")
        return HELP_TYPE
    
    await query.edit_message_text("မှားယွင်းနေပါသည်။ /start ဖြင့်ပြန်စပါ")
    return ConversationHandler.END

async def handle_new_region(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle adding new region."""
    new_region = update.message.text
    if not new_region or len(new_region.strip()) < 2:
        await update.message.reply_text("ကျေးဇူးပြု၍ တိုင်းဒေသအမည်ကိုအပြည့်အစုံရေးပါ:")
        return NEW_REGION
    
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute('INSERT OR IGNORE INTO regions (name) VALUES (?)', (new_region,))
        region_id = c.lastrowid
        conn.commit()
        context.user_data['region_id'] = region_id
        
        await update.message.reply_text("တိုင်းဒေသအသစ်ထည့်သွင်းပြီးပါပြီ!\nကျေးဇူးပြု၍ အကူအညီအမျိုးအစားရွေးပါ (ဥပမာ - ဆေးဝါး, အစားအစာ, သယ်ယူပို့ဆောင်ရေး):")
        return HELP_TYPE
    except Exception as e:
        logger.error(f"Database error: {e}")
        await update.message.reply_text("တိုင်းဒေသထည့်သွင်းရာတွင်အမှားတစ်ခုဖြစ်နေပါသည်။ /start ဖြင့်ပြန်စပါ")
    finally:
        conn.close()
    return ConversationHandler.END

async def handle_help_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle help type selection."""
    help_type = update.message.text
    if not help_type or len(help_type.strip()) < 2:
        await update.message.reply_text("ကျေးဇူးပြု၍ အကူအညီအမျိုးအစားကိုအပြည့်အစုံရေးပါ (ဥပမာ - ဆေးဝါး, အစားအစာ, သယ်ယူပို့ဆောင်ရေး):")
        return HELP_TYPE
    
    context.user_data['help_type'] = help_type
    
    if context.user_data.get('is_volunteer'):
        await update.message.reply_text("ကျေးဇူးပြု၍ သင့်နာမည်ထည့်ပါ:")
    else:
        await update.message.reply_text("ကျေးဇူးပြု၍ ယခုလက်ရှိအခြေနေကိုရေးပါ:")
    return DESCRIPTION

async def handle_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle description input."""
    description = update.message.text
    if not description or len(description.strip()) < 3:
        if context.user_data.get('is_volunteer'):
            await update.message.reply_text("ကျေးဇူးပြု၍ သင့်နာမည်ကိုအပြည့်အစုံရေးပါ:")
        else:
            await update.message.reply_text("ကျေးဇူးပြု၍ ယခုလက်ရှိအခြေနေကိုအပြည့်အစုံရေးပါ:")
        return DESCRIPTION
    
    context.user_data['description'] = description
    await update.message.reply_text("ကျေးဇူးပြု၍ တည်နေရာထည့်ပါ (မြို့နယ်/ရပ်ကွက်/လမ်း):")
    return LOCATION

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle location input."""
    location = update.message.text
    if not location or len(location.strip()) < 3:
        await update.message.reply_text("ကျေးဇူးပြု၍ တည်နေရာကိုအပြည့်အစုံရေးပါ (မြို့နယ်/ရပ်ကွက်/လမ်း):")
        return LOCATION
    
    context.user_data['location'] = location
    await update.message.reply_text("ကျေးဇူးပြု၍ ဖုန်းနံပါတ်ထည့်ပါ (မထည့်လိုပါက 'Skip' ရိုက်ပါ):")
    return PHONE

async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle phone number input."""
    phone = update.message.text if update.message.text.lower() != 'skip' else None
    if phone and (len(phone) < 6 or not any(char.isdigit() for char in phone)):
        await update.message.reply_text("ဖုန်းနံပါတ်မှားယွင်းနေပါသည်။ နံပါတ်များပါဝင်ပါစေ (သို့မဟုတ် 'Skip' ရိုက်ပါ):")
        return PHONE
    
    context.user_data['phone'] = phone
    await update.message.reply_text("ကျေးဇူးပြု၍ Facebook Profile Link ထည့်ပါ (မဖြစ်မနေလိုအပ်ပါသည်):")
    return FB_LINK

async def handle_fb_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Facebook link input."""
    fb_link = update.message.text
    if not fb_link or not ('facebook.com' in fb_link or 'fb.com' in fb_link or fb_link.startswith('http')):
        await update.message.reply_text("မှန်ကန်သော Facebook Profile Link ထည့်ပါ (ဥပမာ - https://facebook.com/yourprofile):")
        return FB_LINK
    
    context.user_data['fb_link'] = fb_link
    await show_confirmation(update, context)
    return CONFIRM

async def show_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show confirmation to user."""
    data = context.user_data
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute('SELECT name FROM regions WHERE id = ?', (data['region_id'],))
        region = c.fetchone()[0]
        
        if data.get('is_volunteer'):
            confirmation_text = f"""
            🤝 အကူအညီပေးသူအတည်ပြုချက်:
            တိုင်းဒေသ: {region}
            အမည်: {data['description']}
            ကူညီမည့်အမျိုးအစား: {data['help_type']}
            တည်နေရာ: {data['location']}
            ဖုန်းနံပါတ်: {data.get('phone', 'မထည့်သွင်းပါ')}
            Facebook Link: {data['fb_link']}
            """
        else:
            confirmation_text = f"""
            🆘 အကူအညီတောင်းခံချက်အတည်ပြုချက်:
            တိုင်းဒေသ: {region}
            အကူအညီအမျိုးအစား: {data['help_type']}
            လက်ရှိအခြေနေ: {data['description']}
            တည်နေရာ: {data['location']}
            ဖုန်းနံပါတ်: {data.get('phone', 'မထည့်သွင်းပါ')}
            Facebook Link: {data['fb_link']}
            """
        
        keyboard = [[InlineKeyboardButton("✅ အတည်ပြုသည်", callback_data='confirm'),
                    InlineKeyboardButton("✏️ ပြန်ပြင်မည်", callback_data='edit')]]
        
        await update.message.reply_text(
            confirmation_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Database error: {e}")
        await update.message.reply_text("ဒေတာဘေ့စ်အမှားတစ်ခုဖြစ်နေပါသည်။ /start ဖြင့်ပြန်စပါ")
    finally:
        conn.close()

async def final_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle final confirmation."""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'confirm':
        user_id = update.effective_user.id
        data = context.user_data
        
        conn = get_db_connection()
        try:
            c = conn.cursor()
            
            if data.get('is_volunteer'):
                # Save volunteer to database
                c.execute('''INSERT INTO volunteers 
                            (user_id, region_id, name, help_type, location, phone, fb_link, status)
                            VALUES (?,?,?,?,?,?,?,?)''',
                            (user_id, data['region_id'], data['description'], 
                             data['help_type'], data['location'], data.get('phone'), 
                             data['fb_link'], 'active'))
                conn.commit()
                
                # Find matching help requests with JOIN
                c.execute('''
                    SELECT hr.*, r.name as region_name 
                    FROM help_requests hr
                    JOIN regions r ON hr.region_id = r.id
                    WHERE hr.region_id = ? 
                    AND hr.help_type = ? 
                    AND hr.status = 'pending'
                    ORDER BY hr.created_at DESC
                ''', (data['region_id'], data['help_type']))
                matching_requests = c.fetchall()
                
                if matching_requests:
                    for req in matching_requests:
                        message = f"""
                        🆘 အကူညီလိုအပ်နေသူရှိပါပြီ!
                        တိုင်းဒေသ: {req[10]} 
                        အကူအညီအမျိုးအစား: {req[3]}
                        အခြေအနေ: {req[5]}
                        တည်နေရာ: {req[4]}
                        ဖုန်း: {req[6] or 'မထည့်ထား'}
                        FB: {req[7]}
                        """
                        await context.bot.send_message(chat_id=user_id, text=message)
                        c.execute('UPDATE help_requests SET status = ? WHERE id = ?', ('matched', req[0]))
                        conn.commit()
                else:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="ယခုအချိန်တွင် အကူညီလိုအပ်နေသူမရှိသေးပါ။ အကူညီလိုအပ်သူရှိလာပါက အသိပေးပါမည်။"
                    )
                
                await query.edit_message_text("အကူအညီပေးသူအချက်အလက်များ အောင်မြင်စွာသိမ်းဆည်းပြီးပါပြီ။")
            
            else:
                # Save help request to database
                c.execute('''INSERT INTO help_requests 
                            (user_id, region_id, help_type, location, description, phone, fb_link, status)
                            VALUES (?,?,?,?,?,?,?,?)''',
                            (user_id, data['region_id'], data['help_type'], 
                             data['location'], data['description'], 
                             data.get('phone'), data['fb_link'], 'pending'))
                conn.commit()
                
                # Find matching volunteers with JOIN
                c.execute('''
                    SELECT v.*, r.name as region_name 
                    FROM volunteers v
                    JOIN regions r ON v.region_id = r.id
                    WHERE v.region_id = ? 
                    AND v.help_type = ? 
                    AND v.status = 'active'
                    ORDER BY v.created_at DESC
                ''', (data['region_id'], data['help_type']))
                matching_volunteers = c.fetchall()
                
                if matching_volunteers:
                    for vol in matching_volunteers:
                        message = f"""
                        🤝 အကူညီပေးသူရှာတွေ့ပါပြီ!
                        တိုင်းဒေသ: {vol[10]} 
                        အမည်: {vol[3]}
                        အကူအညီအမျိုးအစား: {vol[4]}
                        တည်နေရာ: {vol[5]}
                        ဖုန်း: {vol[6] or 'မထည့်ထား'}
                        FB: {vol[7]}
                        """
                        await context.bot.send_message(chat_id=user_id, text=message)
                        c.execute('UPDATE volunteers SET status = ? WHERE id = ?', ('matched', vol[0]))
                        conn.commit()
                else:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="ယခုအချိန်တွင် အကူညီပေးသူမရှိသေးပါ။ အကူညီပေးသူရှိလာပါက အသိပေးပါမည်။"
                    )
                
                await query.edit_message_text("အကူညီတောင်းခံချက် အောင်မြင်စွာသိမ်းဆည်းပြီးပါပြီ။")
            
            context.user_data.clear()
            await start(update, context)
            
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            await query.edit_message_text("အချက်အလက်သိမ်းဆည်းရာတွင် အမှားတစ်ခုဖြစ်နေပါသည်။")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            await query.edit_message_text("မမျှော်လင့်သော အမှားတစ်ခုဖြစ်နေပါသည်။")
        finally:
            conn.close()
    else:
        await start(update, context)
    
    return ConversationHandler.END

async def view_help_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to view all help requests"""
    conn = None
    try:
        if update.message.from_user.id not in ADMIN_IDS:
            await update.message.reply_text("သင့်တွင် ဤ command ကိုသုံးရန် ခွင့်ပြုချက်မရှိပါ။")
            return
    
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute('''
            SELECT hr.*, r.name as region_name 
            FROM help_requests hr
            JOIN regions r ON hr.region_id = r.id
            ORDER BY hr.created_at DESC
        ''')
        
        requests = c.fetchall()
        
        if not requests:
            await update.message.reply_text("🚫 အကူညီတောင်းဆိုမှုမရှိသေးပါ။")
            return
        
        for req in requests:
            message = (
                f"🆘 အကူညီတောင်းဆိုမှု #{req[0]}\n"
                f"တိုင်းဒေသ: {req[10]}\n"  # region_name
                f"အကူအညီအမျိုးအစား: {req[3]}\n"
                f"တည်နေရာ: {req[4]}\n"
                f"အခြေအနေ: {req[5]}\n"
                f"ဖုန်းနံပါတ်: {req[6] or 'မထည့်ထား'}\n"
                f"Facebook: {req[7]}\n"
                f"အခြေအနေ: {req[8]}\n"
                f"ရက်စွဲ: {req[9]}"
            )
            await update.message.reply_text(message)
            
    except sqlite3.Error as e:
        logger.error(f"Database error in /view_requests: {e}")
        await update.message.reply_text("ဒေတာဘေ့စ်မှ အချက်အလက်များရယူရာတွင် အမှားတစ်ခုဖြစ်နေပါသည်။")
    except Exception as e:
        logger.error(f"Unexpected error in /view_requests: {e}")
        await update.message.reply_text("မမျှော်လင့်သော အမှားတစ်ခုဖြစ်နေပါသည်။")
    finally:
        if conn:
            conn.close()

async def view_volunteers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to view all volunteers"""
    conn = None
    try:
        if update.message.from_user.id not in ADMIN_IDS:
            await update.message.reply_text("သင့်တွင် ဤ command ကိုသုံးရန် ခွင့်ပြုချက်မရှိပါ။")
            return
    
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute('''
            SELECT v.*, r.name as region_name 
            FROM volunteers v
            JOIN regions r ON v.region_id = r.id
            ORDER BY v.created_at DESC
        ''')
        
        volunteers = c.fetchall()
        
        if not volunteers:
            await update.message.reply_text("🚫 အကူညီပေးသူမရှိသေးပါ။")
            return
        
        for vol in volunteers:
            message = (
                f"🤝 အကူညီပေးသူ #{vol[0]}\n"
                f"တိုင်းဒေသ: {vol[10]}\n"  # region_name
                f"အမည်: {vol[3]}\n"
                f"အကူအညီအမျိုးအစား: {vol[4]}\n"
                f"တည်နေရာ: {vol[5]}\n"
                f"ဖုန်းနံပါတ်: {vol[6] or 'မထည့်ထား'}\n"
                f"Facebook: {vol[7]}\n"
                f"အခြေအနေ: {vol[8]}"
            )
            await update.message.reply_text(message)
            
    except sqlite3.Error as e:
        logger.error(f"Database error in /view_volunteers: {e}")
        await update.message.reply_text("ဒေတာဘေ့စ်မှ အချက်အလက်များရယူရာတွင် အမှားတစ်ခုဖြစ်နေပါသည်။")
    except Exception as e:
        logger.error(f"Unexpected error in /view_volunteers: {e}")
        await update.message.reply_text("မမျှော်လင့်သော အမှားတစ်ခုဖြစ်နေပါသည်။")
    finally:
        if conn:
            conn.close()

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors and send a message to the user."""
    logger.error(msg="Exception occurred:", exc_info=context.error)
    
    try:
        if update and hasattr(update, 'callback_query'):
            query = update.callback_query
            if query:
                await query.answer()
                await query.edit_message_text("တစ်ခုခုမှားယွင်းနေပါသည်။ /start ဖြင့်ပြန်စပါ")
        elif update and update.message:
            await update.message.reply_text("တစ်ခုခုမှားယွင်းနေပါသည်။ /start ဖြင့်ပြန်စပါ")
    except Exception as e:
        logger.error(f"Error in error handler: {e}")
        
# Modified matching functions to respect notification settings
async def notify_matches(user_id, context, matches, is_volunteer):
    """Send notifications only if enabled"""
    if not is_notification_enabled(user_id):
        logger.info(f"Notifications disabled for user {user_id}")
        return
    
    if is_volunteer:
        for req in matches:
            message = f"""
            🆘 အကူညီလိုအပ်နေသူရှိပါပြီ!
            တိုင်းဒေသ: {req[10]} 
            အကူအညီအမျိုးအစား: {req[3]}
            အခြေအနေ: {req[5]}
            တည်နေရာ: {req[4]}
            ဖုန်း: {req[6] or 'မထည့်ထား'}
            FB: {req[7]}
            """
            await context.bot.send_message(chat_id=user_id, text=message)
    else:
        for vol in matches:
            message = f"""
            🤝 အကူညီပေးသူရှာတွေ့ပါပြီ!
            တိုင်းဒေသ: {vol[10]} 
            အမည်: {vol[3]}
            အကူအညီအမျိုးအစား: {vol[4]}
            တည်နေရာ: {vol[5]}
            ဖုန်း: {vol[6] or 'မထည့်ထား'}
            FB: {vol[7]}
            """
            await context.bot.send_message(chat_id=user_id, text=message)

def main():
    """Start the bot."""
    init_db()
    application = ApplicationBuilder().token(TOKEN).build()

    # Add conversation handler with your original states
    conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start),
                 CallbackQueryHandler(handle_main_selection, pattern='^(need_help|give_help|toggle_noti)$')],
    states={
        REGION: [CallbackQueryHandler(handle_region_selection)],
        NEW_REGION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_region)],
        HELP_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_help_type)],
        DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_description)],
        LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_location)],
        PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone)],
        FB_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_fb_link)],
        CONFIRM: [CallbackQueryHandler(final_confirmation)]
    },
    fallbacks=[CommandHandler('cancel', cancel)]  # cancel function ကိုသုံးထားတယ်
)

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("view_requests", view_help_requests))
    application.add_handler(CommandHandler("view_volunteers", view_volunteers))
    application.add_error_handler(error_handler)

    application.run_polling()

if __name__ == '__main__':
    main()

