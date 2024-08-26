from rest_framework import serializers
from users.models import Branch
from .models import VehicleInstallation
from users.serializers import BranchSerializer


class VehicleInstallationSerializer(serializers.ModelSerializer):
    branch = BranchSerializer(read_only=True)
    branch_id = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(), write_only=True, source='branch'
    )

    class Meta:
        model = VehicleInstallation
        fields = [
            'id', 'owner_name', 'contact_number', 'vehicle_class',
            'registration_number', 'insurance_details', 'datetime_installed',
            'status', 'branch', 'branch_id'
        ]

    def validate_vehicle_class(self, value):
        if value not in dict(VehicleInstallation.VEHICLE_CLASS_CHOICES).keys():
            raise serializers.ValidationError("Invalid vehicle class selected.")
        return value


class RecentVehicleInstallationSerializer(serializers.ModelSerializer):
    branch = BranchSerializer(read_only=True)

    class Meta:
        model = VehicleInstallation
        fields = ['id', 'owner_name', 'contact_number', 'vehicle_class',
                  'registration_number', 'insurance_details', 'datetime_installed',
                  'status', 'branch']
