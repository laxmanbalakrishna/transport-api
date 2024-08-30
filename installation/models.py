import uuid

from django.db import models
from users.models import Branch


# Create your models here.
class VehicleInstallation(models.Model):
    VEHICLE_CLASS_CHOICES = [
        ('Truck', 'Truck'),
        ('Bus', 'Bus'),
        ('Van', 'Van'),
        # Add more vehicle classes/types as needed
    ]

    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
        ('Under Maintenance', 'Under Maintenance'),
        ('Emergency', 'Emergency'),
        # Add more statuses as needed
    ]

    owner_name = models.CharField(max_length=255)
    contact_number = models.CharField(max_length=15)
    vehicle_class = models.CharField(max_length=50, choices=VEHICLE_CLASS_CHOICES)
    registration_number = models.CharField(max_length=20, unique=True)
    insurance_details = models.TextField()
    datetime_installed = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Active')
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, related_name='vehicles')

    def __str__(self):
        return f"{self.registration_number} - {self.vehicle_class}"

    class Meta:
        verbose_name = 'Vehicle Installation'
        verbose_name_plural = 'Vehicle Installations'

class VehicleToken(models.Model):
    vehicle = models.OneToOneField(VehicleInstallation, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)


    def __str__(self):
        return f"Token for {self.vehicle.registration_number}"