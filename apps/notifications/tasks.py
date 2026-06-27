import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from apps.alerts.services import get_alert_event_context

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def send_alert_email(self, event_id):
    try:
        context = get_alert_event_context(event_id)
        subject = f"[ML Monitor] Alert: {context['metric_name']} on {context['experiment_name']}"
        message = (
            f"Metric '{context['metric_name']}' on experiment '{context['experiment_name']}' "
            f"is {context['condition']} threshold {context['threshold']} "
            f"(current value: {context['value']}, run: {context['run_id']})."
        )
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[context['to_email']],
        )
        logger.info('Alert email sent to %s for event %s', context['to_email'], event_id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30, max_retries=3)
