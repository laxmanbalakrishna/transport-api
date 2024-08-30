from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from users.managers import CustomUserManager
import uuid


# Create your models here.
class CustomUser(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    contact_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    date_of_joining = models.DateTimeField(auto_now_add=True, null=True)
    salary_details = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Used for OTP Verification, initially False.
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    last_login = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    objects = CustomUserManager()

    def __str__(self):
        return self.email


class UserTypes(models.Model):
    user_types = [
        ('Admin', 'Admin'),
        ('Manager', 'Manager'),
        ('Normal User', 'Normal User')
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True)
    user_type = models.CharField(max_length=25, choices=user_types)

    # Enforce a one-to-one relationship between Manager and Branch
    branch = models.OneToOneField(
        'Branch', on_delete=models.SET_NULL, null=True, blank=True, unique=True
    )

    def __str__(self):
        return f"{self.user.username} - {self.user_type}"

    def clean(self):
        # Check if the user_type is 'Manager' and ensure only one Manager per branch
        if self.user_type == 'Manager' and self.branch:
            if UserTypes.objects.filter(branch=self.branch).exclude(pk=self.pk).exists():
                raise ValidationError(f"The branch {self.branch.name} already has a Manager assigned.")

    def save(self, *args, **kwargs):
        # Call the clean method to apply the validation
        self.clean()
        super().save(*args, **kwargs)


class Branch(models.Model):
    name = models.CharField(max_length=50, unique=True)
    location = models.CharField(max_length=255, null=True)

    def __str__(self):
        return self.name


class ContactAttempt(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='contact_attempts')
    admin = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='admin_contact_attempts', null=True,
                              blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Contact attempt by {self.user} to {self.admin}"


class Notification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for {self.user.email} at {self.created_at}"
