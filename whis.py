# نصب کتابخانه‌های لازم
!pip install git+https://github.com/openai/whisper.git
!pip install python-telegram-bot ffmpeg-python
!apt update
!apt install -y ffmpeg

import logging
from telegram import Update, InputMediaVideo
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import whisper
import ffmpeg
import os
from tempfile import NamedTemporaryFile
import torch  # برای بررسی CUDA و GPU

# بررسی اینکه آیا CUDA (GPU) نصب است یا خیر
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")  # چاپ دستگاه انتخابی

# بارگذاری مدل Whisper (اگر GPU موجود باشد از آن استفاده می‌کنیم)
model = whisper.load_model("large", device=device)  # مدل "large" که نسخه بزرگ و سریع‌تر است

# تنظیمات ربات تلگرام
os.environ["TELEGRAM_API_TOKEN"] = "7610274621:AAFQHjQbKQrKYrJOHPt07GujXeiw-JOYFa0"  # توکن ربات تلگرام خود را وارد کنید

# راه‌اندازی لاگ‌نویسی
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# تابع برای پردازش و تبدیل صدا به متن
def transcribe_audio(audio_path):
    try:
        result = model.transcribe(audio_path)
        return result['text']
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        return None

# تابع برای تولید فایل SRT (زیرنویس)
def generate_srt(transcription, output_file):
    try:
        with open(output_file, 'w') as f:
            segments = transcription.split('\n')
            for idx, segment in enumerate(segments):
                start_time = idx * 5  # فرض می‌کنیم هر بخش 5 ثانیه طول می‌کشد.
                end_time = (idx + 1) * 5
                f.write(f"{idx+1}\n")
                f.write(f"{format_time(start_time)} --> {format_time(end_time)}\n")
                f.write(f"{segment}\n\n")
        return output_file
    except Exception as e:
        logger.error(f"Error generating subtitles: {e}")
        return None

# تابع برای فرمت‌بندی زمان در فایل SRT
def format_time(seconds):
    m, s = divmod(seconds, 60)
    return f"{int(m):02}:{int(s):02}:00,000"

# تابع برای سوزاندن زیرنویس در ویدیو
def burn_subtitles(video_path, subtitle_path, output_video_path):
    try:
        ffmpeg.input(video_path, subtitles=subtitle_path).output(output_video_path).run()
        return output_video_path
    except Exception as e:
        logger.error(f"Error burning subtitles: {e}")
        return None

# تابع برای شروع ربات
def start(update: Update, context: CallbackContext):
    update.message.reply_text("سلام! فایل صوتی یا ویدیویی ارسال کن تا من برات تبدیل به متن کنم و زیرنویس بسازم.")

# تابع برای پردازش فایل‌های صوتی و ویدیویی
def handle_media(update: Update, context: CallbackContext):
    file = update.message.video or update.message.audio
    if file:
        file_id = file.file_id
        file_name = file.file_name or f"{file_id}.mp4"  # اگر نام فایل وجود نداشت یک نام پیش‌فرض انتخاب می‌کنیم.
        
        file_path = f"/tmp/{file_name}"
        file.download(file_path)
        
        update.message.reply_text("در حال پردازش فایل شما، لطفاً صبر کنید...")

        # اگر فایل صوتی باشد، آن را به متن تبدیل می‌کنیم
        if file.file_name.endswith(('mp3', 'wav', 'ogg')):
            transcription = transcribe_audio(file_path)
            if transcription:
                srt_file = "/tmp/subtitles.srt"
                generate_srt(transcription, srt_file)
                update.message.reply_text("زیرنویس تولید شد! در حال ارسال...")
                update.message.reply_document(document=open(srt_file, 'rb'))
        
        # اگر فایل ویدیویی باشد، ابتدا آن را تبدیل به صوت کرده و سپس پردازش می‌کنیم
        elif file.file_name.endswith(('mp4', 'mov', 'avi')):
            audio_file_path = f"/tmp/{file_id}.mp3"
            ffmpeg.input(file_path).output(audio_file_path).run()
            transcription = transcribe_audio(audio_file_path)
            if transcription:
                srt_file = "/tmp/subtitles.srt"
                generate_srt(transcription, srt_file)
                output_video = "/tmp/output_video.mp4"
                burned_video = burn_subtitles(file_path, srt_file, output_video)
                if burned_video:
                    update.message.reply_text("ویدیو با زیرنویس تولید شد! در حال ارسال...")
                    update.message.reply_video(video=open(burned_video, 'rb'))

# راه‌اندازی ربات و فرمان‌ها
def main():
    updater = Updater(token=os.getenv("TELEGRAM_API_TOKEN"), use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.audio | Filters.video, handle_media))
    
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()