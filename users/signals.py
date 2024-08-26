from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserTypes


@receiver(post_migrate)
def create_administator_user(sender, **kwargs):
    User = get_user_model()
    if not User.objects.filter(usertypes__user_type='Admin').exists():
        admin_user = User.objects.create(
            username='Admin',
            email='admin@bdnt.tech',
            is_active=True,
        )
        admin_user.set_password('Admin@123')
        admin_user.save()
        UserTypes.objects.create(
            user=admin_user,
            user_type='Admin',
        )
