from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_trade_settings(sender, instance, created, **kwargs):
    if created:
        UserTradeSettings.objects.create(user=instance)