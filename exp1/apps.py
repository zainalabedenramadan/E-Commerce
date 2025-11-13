from django.apps import AppConfig


class Exp1Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'exp1'
    def ready(self):
        import exp1.signals