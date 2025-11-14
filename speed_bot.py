import os
import asyncio
import random
import time
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from collections import defaultdict

# إعدادات البوت - استخدم متغيرات البيئة في Railway
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8445989265:AAE73bRecYTD8QLBnLNn7kgb7P2hxhp4CNQ")
TARGET_BOT_USERNAME = "NKKKKKL_BOT"  # بدون @

# تخزين البيانات
speed_tasks = {}
speed_enabled = defaultdict(bool)

class SpeedBot:
    def __init__(self):
        self.active_chats = set()
    
    def calculate_typing_speed(self, base_wpm=160):
        fluctuation = random.uniform(-0.1, 0.1)
        final_wpm = base_wpm * (1 + fluctuation)
        return max(120, min(220, final_wpm))
    
    def is_speed_sentence(self, text):
        if not text or len(text.strip()) < 10:
            return False
        
        if '،' in text:
            words = text.split('،')
            if len(words) >= 3:
                return True
        
        if re.search(r'\w+\(\d+\)', text):
            return True
            
        return False
    
    def build_speed_output(self, sentence):
        if '،' in sentence:
            return sentence
        
        if re.search(r'\w+\(\d+\)', sentence):
            return sentence
            
        return None
    
    async def speed_type_sentence(self, context, chat_id, sentence, wpm, start_time):
        try:
            speed_text = self.build_speed_output(sentence)
            if not speed_text:
                return 0
                
            if '،' in speed_text:
                parts = speed_text.split('،')
            else:
                parts = [speed_text]
            
            parts = [part.strip() for part in parts if part.strip()]
            
            if not parts:
                return 0
            
            total_chars = sum(len(part) for part in parts)
            chars_per_second = (wpm * 5) / 60.0
            total_time_needed = total_chars / chars_per_second
            chunk_delay = total_time_needed / len(parts)
            
            message = None
            current_text = ""
            
            for i, part in enumerate(parts):
                if not speed_enabled[chat_id]:
                    break
                    
                if i > 0:
                    jitter = random.uniform(0.8, 1.2)
                    await asyncio.sleep(chunk_delay * jitter)
                
                if current_text:
                    current_text += '، ' + part
                else:
                    current_text = part
                
                try:
                    if message is None:
                        message = await context.bot.send_message(
                            chat_id=chat_id, 
                            text=current_text
                        )
                    else:
                        await message.edit_text(current_text)
                except Exception as e:
                    print(f"Error editing: {e}")
                    break
            
            if not speed_enabled[chat_id]:
                try:
                    if message:
                        await message.delete()
                except:
                    pass
                return 0
            
            elapsed_time = time.time() - start_time
            word_count = len([p for p in parts if p.strip()])
            actual_wpm = (word_count / elapsed_time) * 60 if elapsed_time > 0 else 0
            
            final_text = f"{current_text}\n\n⚡ Speed: {actual_wpm:.1f} WPM"
            try:
                if message:
                    await message.edit_text(final_text)
            except:
                pass
            
            return actual_wpm
            
        except asyncio.CancelledError:
            print(f"Task cancelled for chat {chat_id}")
            raise
        except Exception as e:
            print(f"Error: {e}")
            return 0
    
    async def trigger_speed_bot(self, context, chat_id, sentence):
        try:
            if not speed_enabled[chat_id]:
                return
                
            if not self.is_speed_sentence(sentence):
                return
            
            task_key = str(chat_id)
            old_task = speed_tasks.get(task_key)
            if old_task:
                if not old_task.done():
                    old_task.cancel()
                    try:
                        await old_task
                    except asyncio.CancelledError:
                        pass
                speed_tasks.pop(task_key, None)
            
            wpm = self.calculate_typing_speed()
            start_time = time.time()
            
            task = asyncio.create_task(
                self.speed_type_sentence(context, chat_id, sentence, wpm, start_time)
            )
            speed_tasks[task_key] = task
            
            def cleanup_task(t, key=task_key):
                if speed_tasks.get(key) is t:
                    speed_tasks.pop(key, None)
            
            task.add_done_callback(cleanup_task)
            
        except Exception as e:
            print(f"Error: {e}")

speed_bot = SpeedBot()

async def handle_target_bot_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message
        if not message or not message.text:
            return
        
        chat_id = message.chat_id
        
        if message.from_user and message.from_user.username:
            if message.from_user.username.lower() == TARGET_BOT_USERNAME.lower():
                sentence = message.text.strip()
                print(f"Target bot message: {sentence}")
                await speed_bot.trigger_speed_bot(context, chat_id, sentence)
                    
    except Exception as e:
        print(f"Error: {e}")

async def speed_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    
    if speed_enabled[chat_id]:
        await update.message.reply_text("✅ Already active!")
        return
    
    speed_enabled[chat_id] = True
    await update.message.reply_text(f"🚀 **Speed activated!**\n\nNow tracking @{TARGET_BOT_USERNAME}")

async def speed_stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    
    if not speed_enabled[chat_id]:
        await update.message.reply_text("❌ Already stopped!")
        return
    
    speed_enabled[chat_id] = False
    
    task_key = str(chat_id)
    old_task = speed_tasks.get(task_key)
    if old_task:
        if not old_task.done():
            old_task.cancel()
            try:
                await old_task
            except asyncio.CancelledError:
                pass
        speed_tasks.pop(task_key, None)
    
    await update.message.reply_text("⏹️ **Speed stopped!**")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = f"""
🚀 **Speed Bot**

Tracking @{TARGET_BOT_USERNAME} only.

⚡ **Commands:**
/start - Show this
/speed - Start speed
/speed stop - Stop speed

🎯 **Target:** @{TARGET_BOT_USERNAME}
    """
    await update.message.reply_text(welcome_text)

async def post_init(application):
    print("🚀 Bot starting on Railway...")
    print(f"🎯 Target: @{TARGET_BOT_USERNAME}")

def main():
    # التحقق من التوكن
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Error: BOT_TOKEN not set!")
        return
    
    print("🚀 Starting Speed Bot...")
    print(f"🎯 Target bot: @{TARGET_BOT_USERNAME}")
    
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("speed", speed_start_command))
    app.add_handler(CommandHandler("سبيد", speed_start_command))
    
    app.add_handler(MessageHandler(
        filters.Regex(r'^(speed stop|سبيد وقف)$'),
        speed_stop_command
    ))
    
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_target_bot_messages
    ))
    
    print("✅ Bot is running on Railway!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
