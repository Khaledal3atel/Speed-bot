import asyncio
import random
import time
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from collections import defaultdict

BOT_TOKEN = "8445989265:AAE73bRecYTD8QLBnLNn7kgb7P2hxhp4CNQ"

speed_tasks = {}
speed_enabled = defaultdict(bool)

class SpeedBot:
    def calculate_typing_speed(self):
        return random.randint(150, 200)
    
    def is_speed_sentence(self, text):
        return '،' in text or '(' in text
    
    async def speed_type_sentence(self, context, chat_id, sentence, wpm, start_time):
        try:
            if '،' in sentence:
                parts = sentence.split('،')
            else:
                parts = [sentence]
            
            parts = [p.strip() for p in parts if p.strip()]
            
            message = None
            current_text = ""
            
            for i, part in enumerate(parts):
                if not speed_enabled[chat_id]:
                    break
                    
                if i > 0:
                    await asyncio.sleep(0.5)
                
                if current_text:
                    current_text += '، ' + part
                else:
                    current_text = part
                
                try:
                    if message is None:
                        message = await context.bot.send_message(chat_id=chat_id, text=current_text)
                    else:
                        await message.edit_text(current_text)
                except:
                    break
            
            if speed_enabled[chat_id] and message:
                elapsed = time.time() - start_time
                wpm = (len(parts) / elapsed) * 60 if elapsed > 0 else 0
                final = f"{current_text}\n\nسرعة: {wpm:.1f}"
                await message.edit_text(final)
            
        except Exception as e:
            print(f"خطأ: {e}")

speed_bot = SpeedBot()

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message
        if not message or not message.text:
            return
        
        chat_id = message.chat_id
        sentence = message.text.strip()
        
        if speed_enabled[chat_id] and speed_bot.is_speed_sentence(sentence):
            task_key = str(chat_id)
            old_task = speed_tasks.get(task_key)
            if old_task:
                old_task.cancel()
            
            wpm = speed_bot.calculate_typing_speed()
            task = asyncio.create_task(
                speed_bot.speed_type_sentence(context, chat_id, sentence, wpm, time.time())
            )
            speed_tasks[task_key] = task
                    
    except:
        pass

async def start_speed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    speed_enabled[chat_id] = True
    await update.message.reply_text("🚀 تم تشغيل السبيد")

async def stop_speed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    speed_enabled[chat_id] = False
    task_key = str(chat_id)
    if task_key in speed_tasks:
        speed_tasks[task_key].cancel()
    await update.message.reply_text("⏹️ تم إيقاف السبيد")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("اكتب /سبيد لتشغيل السبيد")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("speed", start_speed))
    app.add_handler(CommandHandler("سبيد", start_speed))
    app.add_handler(MessageHandler(filters.Regex(r'^(speed stop|سبيد وقف)$'), stop_speed))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
    
    print("البوت شغال")
    app.run_polling()

if __name__ == "__main__":
    main()
