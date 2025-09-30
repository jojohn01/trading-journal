"""
Django signal handlers for the journal app.
Includes automatic creation of user trade settings and syncing user email with primary EmailAddress.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import UserTradeSettings


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_trade_settings(sender, instance, created, **kwargs):
    """Create UserTradeSettings instance when a new user is created."""
    if created:
        UserTradeSettings.objects.create(user=instance)

@receiver(post_save, sender=EmailAddress)
def sync_primary_email_to_user(sender, instance: EmailAddress, created, **kwargs):
    """Sync User.email to the primary EmailAddress and optionally auto-verify social emails."""
    user = instance.user

    auto_verify_social = (
        isinstance(getattr(settings, "SOCIALACCOUNT_EMAIL_VERIFICATION", None), str)
        and settings.SOCIALACCOUNT_EMAIL_VERIFICATION.lower() == "none"
    )
    if created and auto_verify_social and not instance.verified:
        instance.verified = True
        instance.save(update_fields=["verified"])

    if instance.primary and user.email != instance.email:
        user.email = instance.email
        user.save(update_fields=["email"])