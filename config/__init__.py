from .celery import app as celery_app

# Ini memastikan aplikasi Celery selalu dimuat saat Django start
__all__ = ('celery_app',)