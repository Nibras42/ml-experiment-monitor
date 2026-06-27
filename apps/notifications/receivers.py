from django.dispatch import receiver

from apps.alerts.signals import alert_triggered

from .tasks import send_alert_email


@receiver(alert_triggered)
def handle_alert_triggered(sender, event, **kwargs):
    send_alert_email.delay(str(event.id))
