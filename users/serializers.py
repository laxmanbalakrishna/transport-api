from rest_framework import serializers
from .models import CustomUser, UserTypes, Branch, ContactAttempt, Notification
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.response import Response


class UserTypesSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserTypes
        fields = ['user_type', 'branch']


class CustomUserSerializer(serializers.ModelSerializer):
    user_type = serializers.CharField(write_only=True)
    branch = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(),
        write_only=True,
        required=False,
        allow_null=True
    )
    salary_details = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'username', 'password', 'date_of_joining', 'user_type', 'branch', 'salary_details']
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def validate(self, data):
        user_type = data.get('user_type')
        branch = data.get('branch')

        # Validate the user_type
        if user_type not in dict(UserTypes._meta.get_field('user_type').choices).keys():
            raise serializers.ValidationError(f"Invalid user type: {user_type}.")

        # Specific validations for Manager user type
        if user_type == 'Manager':
            if not branch:
                raise serializers.ValidationError("Branch must be provided for a Manager.")

            # Ensure the branch does not already have a Manager
            if UserTypes.objects.filter(user_type='Manager', branch=branch).exists():
                raise serializers.ValidationError(f"The branch '{branch.name}' already has a Manager.")
        else:
            if branch:
                raise serializers.ValidationError(
                    f"A branch cannot be assigned to a user with the '{user_type}' user type.")

        return data

    def create(self, validated_data):
        user_type = validated_data.pop('user_type')
        branch = validated_data.pop('branch', None)
        password = validated_data.pop('password')

        # Create and save the user after all validations have passed
        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()

        # Create UserType instance
        UserTypes.objects.create(user=user, user_type=user_type, branch=branch if user_type == 'Manager' else None)

        return user

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        try:
            user_type_instance = UserTypes.objects.get(user=instance)
            representation['user_type'] = user_type_instance.user_type
            representation['branch'] = user_type_instance.branch.name if user_type_instance.branch else ""
        except UserTypes.DoesNotExist:
            representation['user_type'] = ""
            representation['branch'] = ""

        # Include salary_details in the response
        representation['salary_details'] = instance.salary_details

        return representation


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        # Perform basic validation
        if not email or not password:
            raise serializers.ValidationError("Both email and password are required.")

        return data


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ['id', 'name', 'location']


class ManagerSerializer(serializers.ModelSerializer):
    branch = BranchSerializer()  # Include the branch information

    class Meta:
        model = UserTypes
        fields = ['user', 'branch']

    user = serializers.SerializerMethodField()

    def get_user(self, obj):
        return {
            'username': obj.user.username,
            'email': obj.user.email,
            'date_of_joining': obj.user.date_of_joining,
            'salary_details': obj.user.salary_details
        }


class ContactAttemptSerializer(serializers.ModelSerializer):
    admin = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.filter(usertypes__user_type='Admin'))

    class Meta:
        model = ContactAttempt
        fields = ['admin', 'message']

    def create(self, validated_data):
        user = self.context['request'].user
        return ContactAttempt.objects.create(user=user, **validated_data)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'message', 'created_at', 'is_read']
