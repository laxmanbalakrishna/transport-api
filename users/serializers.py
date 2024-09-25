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
    salary_details = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)

    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'username', 'password','contact_number','date_of_joining', 'user_type', 'branch', 'salary_details']
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

class CustomUserUpdateSerializer(serializers.ModelSerializer):
    user_type = serializers.CharField(write_only=True, required=False)
    branch = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    contact_number = serializers.CharField(required=False, allow_blank=True)  # Added contact_number field

    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'username', 'password', 'date_of_joining', 'salary_details', 'user_type', 'branch', 'contact_number']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
            'email': {'required': False},
            'username': {'required': False},
            'date_of_joining': {'required': False},
            'salary_details': {'required': False},
            'contact_number': {'required': False},  # Added extra_kwargs for contact_number
        }

    def validate(self, data):
        user = self.instance
        request_user = self.context['request'].user
        errors = {}

        # Ensure the user type exists
        try:
            user_type_instance = UserTypes.objects.get(user=user)
            request_user_type_instance = UserTypes.objects.get(user=request_user)
        except UserTypes.DoesNotExist:
            raise serializers.ValidationError("User does not have a valid user type assigned.")

        if user == request_user:
            # Validation for user updating their own profile
            if 'user_type' in data:
                errors['user_type'] = "You cannot change your own user type."
            if 'branch' in data:
                errors['branch'] = "You cannot change your own branch."

            if request_user_type_instance.user_type == 'Admin':
                for field in ['date_of_joining', 'salary_details']:
                    if field in data:
                        errors[field] = f"{field.replace('_', ' ').title()} cannot be changed by Admins."

            elif request_user_type_instance.user_type == 'Manager':
                for field in ['date_of_joining', 'salary_details', 'user_type', 'branch']:
                    if field in data:
                        errors[field] = f"{field.replace('_', ' ').title()} cannot be changed by Managers."

        else:
            # Validation for admins updating other users' profiles
            if request_user_type_instance.user_type == 'Admin':
                if 'user_type' in data and data['user_type'] == 'Admin':
                    errors['user_type'] = "Cannot change user type to 'Admin'."
                if 'branch' in data:
                    branch_id = data.get('branch')
                    if branch_id and UserTypes.objects.filter(branch_id=branch_id).exclude(user=user).exists():
                        errors['branch'] = "The branch is already assigned to another user."

            # Validation for managers updating other users' profiles
            elif request_user_type_instance.user_type == 'Manager':
                if user_type_instance.user_type == 'Admin':
                    errors['non_field_errors'] = "Managers cannot update Admin profiles."

        if errors:
            raise serializers.ValidationError(errors)

        return data

    def update(self, instance, validated_data):
        if 'password' in validated_data:
            instance.set_password(validated_data.pop('password'))

        # Update the user instance with other valid data
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Handle user_type and branch updates separately
        user_type = validated_data.pop('user_type', None)
        branch_id = validated_data.pop('branch', None)

        if user_type or branch_id is not None:
            user_type_instance = UserTypes.objects.get(user=instance)
            if user_type:
                user_type_instance.user_type = user_type
            if branch_id is not None:
                branch = Branch.objects.get(id=branch_id) if branch_id else None
                user_type_instance.branch = branch
            user_type_instance.save()

        instance.save()
        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        try:
            user_type_instance = UserTypes.objects.get(user=instance)
            representation['user_type'] = user_type_instance.user_type
            representation['branch'] = user_type_instance.branch.name if user_type_instance.branch else None
        except UserTypes.DoesNotExist:
            representation['user_type'] = ""
            representation['branch'] = None

        representation['salary_details'] = instance.salary_details
        representation['contact_number'] = instance.contact_number  # Added contact_number to representation

        return representation




class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ['id', 'name', 'location']


class ListAdminManagerSerializer(serializers.ModelSerializer):
    branch = BranchSerializer()  # Include the branch information

    class Meta:
        model = UserTypes
        fields = ['user', 'branch']

    user = serializers.SerializerMethodField()

    def get_user(self, obj):
        return {
            'id':obj.user.id,
            'username': obj.user.username,
            'email': obj.user.email,
            'date_of_joining': obj.user.date_of_joining,
            'salary_details': obj.user.salary_details
        }


class ContactAttemptSerializer(serializers.ModelSerializer):
    admin = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.filter(usertypes__user_type='Admin'))
    user = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = ContactAttempt
        fields = ['id','admin', 'user', 'message', 'created_at']

    def create(self, validated_data):
        user = self.context['request'].user
        return ContactAttempt.objects.create(user=user, **validated_data)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'message', 'created_at', 'is_read']


class OTPRequestUserSerializer(serializers.Serializer):
    contact_number = serializers.CharField(max_length=15)

    def validate_contact_number(self, value):
        if not CustomUser.objects.filter(contact_number=value).exists():
            raise serializers.ValidationError("Contact number is not registered.")
        return value

class OTPVerifyUserSerializer(serializers.Serializer):
    contact_number = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=6)