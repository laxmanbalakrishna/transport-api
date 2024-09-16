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
            'status', 'branch', 'branch_id', 'user_type'
        ]

    def validate_vehicle_class(self, value):
        if value not in dict(VehicleInstallation.VEHICLE_CLASS_CHOICES).keys():
            raise serializers.ValidationError("Invalid vehicle class selected.")
        return value

# For Normal users Otp based login
class OTPRequestSerializer(serializers.Serializer):
    contact_number = serializers.CharField(max_length=15)

    def validate_contact_number(self, value):
        if not VehicleInstallation.objects.filter(contact_number=value).exists():
            raise serializers.ValidationError("Contact number is not registered.")
        return value

class OTPVerifySerializer(serializers.Serializer):
    contact_number = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=6)

# end for serializers for normal user login


class RecentVehicleInstallationSerializer(serializers.ModelSerializer):
    branch = BranchSerializer(read_only=True)

    class Meta:
        model = VehicleInstallation
        fields = ['id', 'owner_name', 'contact_number', 'vehicle_class',
                  'registration_number', 'insurance_details', 'datetime_installed',
                  'status', 'branch']
