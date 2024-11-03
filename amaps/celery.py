from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'amaps.prod')

app = Celery('amaps')
app.conf.enable_utc = False
app.conf.update(timezone = 'Africa/Lagos')
app.config_from_object(settings, namespace='CELERY')

# Celery beat scheduler
app.conf.beat_schedule = {
    'update-all-exchange-rates': {
        'task': 'walletservice.tasks.update_exchange_rates',
        'schedule': crontab(hour=0, minute=0), 
        # 'schedule': crontab(minute='*/2'), 
    },
}


app.autodiscover_tasks()
