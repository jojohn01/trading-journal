from django.db.models.signals import post_save
from django.dispatch import receiver
from allauth.account.models import EmailAddress
from django.conf import settings 

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_trade_settings(sender, instance, created, **kwargs):
    if created:
        UserTradeSettings.objects.create(user=instance)

@receiver(post_save, sender=EmailAddress)
def sync_primary_email_to_user(sender, instance: EmailAddress, **kwargs):
    # Keep User.email in sync with the primary EmailAddress
    if instance.primary:
        user = instance.user
        if user.email != instance.email:
            user.email = instance.email
            user.save(update_fields=["email"])

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_emailaddress_for_user(sender, instance, created, **kwargs):
    if not instance.email:
        return
    # Only create if none exists
    if not EmailAddress.objects.filter(user=instance, email=instance.email).exists():
        EmailAddress.objects.create(
            user=instance,
            email=instance.email,
            primary=True,
            verified=False,   # set True if you trust admin-entered emails
        )