import asyncio
import random
import time
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from collections import defaultdict

# إعدادات البوت
BOT_TOKEN = "8445989265:AAE73bRecYTD8QLBnLNn7kgb7P2hxhp4CNQ"
TARGET_BOT_USERNAME = "@NKKKKKL_BOT"  # البوت اللي تتابعه

# تخزين البيانات
speed_tasks = {}
speed_enabled = defaultdict(bool)  # {chat_id: True/False}

class SpeedBot:
    def __init__(self):
        self.active_chats = set()
    
    def calculate_typing_speed(self, base_wpm=160):
        """حساب سرعة الكتابة مع تقلبات عشوائية"""
        fluctuation = random.uniform(-0.1, 0.1)
        final_wpm = base_wpm * (1 + fluctuation)
        return max(120, min(220, final_wpm))
    
    def is_speed_sentence(self, text):
        """التأكد إذا كانت الجملة من نوع السبيد (تحتوي على ، بين الكلمات)"""
        if not text or len(text.strip()) < 10:
            return False
        
        # البحث عن فواصل عربية بين الكلمات
        if '،' in text:
            words = text.split('،')
            if len(words) >= 3:  # على الأقل 3 كلمات مفصولة بفواصل
                return True
        
        # أو إذا كانت تحتوي على نمط التكرار (كلمة(رقم))
        if re.search(r'\w+\(\d+\)', text):
            return True
            
        return False
    
    def build_speed_output(self, sentence):
        """بناء النص بشكل متقطع للعرض التدريجي"""
        # إذا كانت الجملة تحتوي على فواصل، نستخدمها كما هي
        if '،' in sentence:
            return sentence
        
        # إذا كانت نمط تكرار، نعيدها كما هي
        if re.search(r'\w+\(\d+\)', sentence):
            return sentence
            
        # إذا لم تكن من النوعين، لا نعيد شيء
        return None
    
    async def speed_type_sentence(self, context, chat_id, sentence, wpm, start_time):
        """محاكاة الكتابة بسرعة"""
        try:
            speed_text = self.build_speed_output(sentence)
            if not speed_text:
                return 0
                
            # تقسيم النص إلى أجزاء بناءً على الفواصل
            if '،' in speed_text:
                parts = speed_text.split('،')
            else:
                parts = [speed_text]
            
            # تنظيف الأجزاء من المسافات الزائدة
            parts = [part.strip() for part in parts if part.strip()]
            
            if not parts:
                return 0
            
            total_chars = sum(len(part) for part in parts)
            
            # حساب الوقت المطلوب
            chars_per_second = (wpm * 5) / 60.0
            total_time_needed = total_chars / chars_per_second
            
            chunk_delay = total_time_needed / len(parts)
            
            # إرسال الرسائل بشكل متقطع
            message = None
            current_text = ""
            
            for i, part in enumerate(parts):
                # التحقق إذا تم إيقاف السبيد أثناء الكتابة
                if not speed_enabled[chat_id]:
                    break
                    
                if i > 0:
                    # إضافة تأخير عشوائي بين الأجزاء
                    jitter = random.uniform(0.8, 1.2)
                    await asyncio.sleep(chunk_delay * jitter)
                
                # بناء النص التدريجي
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
                    print(f"خطأ في التحرير: {e}")
                    break
            
            # إذا تم إيقاف السبيد، لا نعرض النتيجة
            if not speed_enabled[chat_id]:
                try:
                    if message:
                        await message.delete()
                except:
                    pass
                return 0
            
            # حساب السرعة النهائية
            elapsed_time = time.time() - start_time
            word_count = len([p for p in parts if p.strip()])
            actual_wpm = (word_count / elapsed_time) * 60 if elapsed_time > 0 else 0
            
            # عرض النتيجة النهائية
            final_text = f"{current_text}\n\n⚡ سرعة السبيد: {actual_wpm:.1f} كلمة/دقيقة"
            try:
                if message:
                    await message.edit_text(final_text)
            except:
                pass
            
            return actual_wpm
            
        except asyncio.CancelledError:
            print(f"تم إلغاء مهمة السبيد في الدردشة {chat_id}")
            raise
        except Exception as e:
            print(f"خطأ في speed_type_sentence: {e}")
            return 0
    
    async def trigger_speed_bot(self, context, chat_id, sentence):
        """تشغيل السبيد على جملة محددة"""
        try:
            # التأكد أن السبيد مفعل في هذه الدردشة
            if not speed_enabled[chat_id]:
                return
                
            # التأكد أن الجملة من نوع السبيد
            if not self.is_speed_sentence(sentence):
                return
            
            # إلغاء أي مهمة سابقة في نفس الدردشة
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
            
            # حساب السرعة
            wpm = self.calculate_typing_speed()
            start_time = time.time()
            
            # بدء المهمة الجديدة
            task = asyncio.create_task(
                self.speed_type_sentence(context, chat_id, sentence, wpm, start_time)
            )
            speed_tasks[task_key] = task
            
            # تنظيف المهمة عند الانتهاء
            def cleanup_task(t, key=task_key):
                if speed_tasks.get(key) is t:
                    speed_tasks.pop(key, None)
            
            task.add_done_callback(cleanup_task)
            
        except Exception as e:
            print(f"خطأ في تشغيل السبيد: {e}")

# إنشاء الكائن الرئيسي
speed_bot = SpeedBot()

async def handle_target_bot_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التعامل مع رسائل البوت المستهدف فقط"""
    try:
        message = update.message
        if not message or not message.text:
            return
        
        chat_id = message.chat_id
        
        # التحقق إذا كانت الرسالة من البوت المستهدف
        if message.from_user and message.from_user.username:
            if message.from_user.username.lower() == TARGET_BOT_USERNAME.replace("@", "").lower():
                sentence = message.text.strip()
                
                print(f"📝 جملة من البوت المستهدف: {sentence}")
                
                # تشغيل السبيد على الجملة (إذا كانت من نوع السبيد)
                await speed_bot.trigger_speed_bot(context, chat_id, sentence)
                    
    except Exception as e:
        print(f"خطأ في handle_target_bot_messages: {e}")

async def speed_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تشغيل السبيد"""
    chat_id = update.message.chat_id
    
    if speed_enabled[chat_id]:
        await update.message.reply_text("✅ السبيد شغال بالفعل!")
        return
    
    speed_enabled[chat_id] = True
    await update.message.reply_text(f"🚀 **تم تشغيل السبيد!**\n\nالآن سأتابع البوت {TARGET_BOT_USERNAME} وأكتب الجمل التي تحتوي على فواصل (،) أو أنماط تكرار.")

async def speed_stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إيقاف السبيد"""
    chat_id = update.message.chat_id
    
    if not speed_enabled[chat_id]:
        await update.message.reply_text("❌ السبيد متوقف بالفعل!")
        return
    
    speed_enabled[chat_id] = False
    
    # إلغاء أي مهمة شغالة
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
    
    await update.message.reply_text("⏹️ **تم إيقاف السبيد!**")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر البدء"""
    welcome_text = f"""
    🚀 **بوت السبيد المتخصص**
    
    أنا بوت السبيد! سأتابع البوت {TARGET_BOT_USERNAME} فقط وأكتب الجمل بسرعة متقطعة.
    
    ⚡ **الأوامر المتاحة:**
    /سبيد - تشغيل نظام السبيد
    /سبيد وقف - إيقاف نظام السبيد
    /start - عرض هذه الرسالة
    
    🎯 **البوت المستهدف:** {TARGET_BOT_USERNAME}
    
    📝 **أنواع الجمل التي سأكتبها:**
    - الجمل التي بين كلماتها فواصل عربية (،)
    - أنماط التكرار مثل: كلمة(3) كلمة(2)
    
    🔥 **لتبدأ، اكتب:** /سبيد
    """
    
    await update.message.reply_text(welcome_text)

def main():
    """الدالة الرئيسية"""
    print("🚀 بدء تشغيل بوت السبيد المتخصص...")
    print(f"🎯 البوت المستهدف: {TARGET_BOT_USERNAME}")
    print("⚡ البوت يشتغل بأمر /سبيد ويوقف بأمر /سبيد وقف")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("سبيد", speed_start_command))
    app.add_handler(CommandHandler("speed", speed_start_command))
    
    # handler خاص لأمر "سبيد وقف"
    app.add_handler(MessageHandler(
        filters.Regex(r'^سبيد وقف$') | filters.Regex(r'^/سبيد وقف$'),
        speed_stop_command
    ))
    
    # متابعة رسائل البوت المستهدف فقط
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_target_bot_messages
    ))
    
    print(f"✅ البوت يعمل! سيتابع {TARGET_BOT_USERNAME} فقط")
    print("📝 اكتب /سبيد لبدء التشغيل")
    app.run_polling()

if __name__ == "__main__":
    main()
