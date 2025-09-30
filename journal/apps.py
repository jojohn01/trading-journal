from django.apps import AppConfig


class JournalConfig(AppConfig):
    """AppConfig for the journal app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'journal'

    def ready(self):
        import journal.signals  # noqa
