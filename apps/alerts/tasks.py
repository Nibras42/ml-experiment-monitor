import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def check_alert_thresholds(self):
    from .models import AlertRule
    from .services import evaluate_rule

    try:
        triggered = 0
        for rule in AlertRule.objects.filter(is_active=True).select_related('experiment', 'user'):
            if evaluate_rule(rule):
                triggered += 1
        logger.info('Alert threshold check complete: %s triggered', triggered)
        return triggered
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30, max_retries=3)
