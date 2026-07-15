import os
from celery import shared_task
from celery.signals import setup_logging
from celery.schedules import crontab

# Tetapkan default settings module Django untuk celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Buat instance aplikasi Celery dengan nama modul bawaan
import celery
app = celery.Celery('config')

# Membaca konfigurasi dari settings.py dengan prefix 'CELERY_'
app.config_from_object('django.conf:settings', namespace='CELERY')

# Muat semua berkas tasks.py yang ada di setiap aplikasi Django secara otomatis
app.autodiscover_tasks()

# ⏰ Konfigurasi Scheduled Tasks (Celery Beat)
app.conf.beat_schedule = {
    'update-course-stats-every-hour': {
        'task': 'courses.tasks.update_course_statistics',
        'schedule': crontab(minute=0, hour='*'), # Berjalan otomatis setiap jam
    },
}