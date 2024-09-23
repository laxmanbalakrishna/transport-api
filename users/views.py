from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.hashers import check_password

from installation.models import VehicleInstallation
from .serializers import (CustomUserSerializer, LoginSerializer, BranchSerializer, ListAdminManagerSerializer,
                          ContactAttemptSerializer, NotificationSerializer, CustomUserUpdateSerializer,
                          OTPRequestUserSerializer, OTPVerifyUserSerializer)
from .models import UserTypes, Branch, ContactAttempt, CustomUser, Notification
from rest_framework.authtoken.models import Token
from installation.utils import IsAdminUser, IsAdminOrManager
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail, BadHeaderError
from smtplib import SMTPException
from .utils import generate_otp, send_otp_via_twilio, verify_otp


class UserRegistrationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            user_type = UserTypes.objects.get(user=request.user).user_type
            if user_type != 'Admin':
                return Response({"message": "Only Admin users can create new users."}, status=status.HTTP_403_FORBIDDEN)
        except UserTypes.DoesNotExist:
            return Response({"message": "User does not have a valid user type assigned."},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = CustomUserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class LoginView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']

            UserModel = get_user_model()
            try:
                user = UserModel.objects.get(email=email)
                if user.check_password(password):
                    # Manually allow login even if is_active is False
                    token, created = Token.objects.get_or_create(user=user)

                    # Fetch the user type and branch information
                    user_type_instance = UserTypes.objects.filter(user=user).first()

                    return Response({
                        "message": "Login successful.",
                        "token": token.key,
                        "user_id": user.id,
                        "email": user.email,
                        "username": user.username,
                        "contact_number":user.contact_number,
                        "user_type": user_type_instance.user_type if user_type_instance else None,
                        "branch": user_type_instance.branch.name if user_type_instance and user_type_instance.branch else None
                    }, status=status.HTTP_200_OK)
            except UserModel.DoesNotExist:
                pass

            return Response({"non_field_errors": ["Invalid email or password."]}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            # Delete the user's token to logout
            request.user.auth_token.delete()
            return Response({'message': 'Successfully logged out.'}, status=status.HTTP_200_OK)
        except Token.DoesNotExist:
            return Response({'message': 'User is not logged in.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        data = request.data

        # Get the old and new passwords from the request data
        old_password = data.get("old_password")
        new_password = data.get("new_password")
        confirm_password = data.get("confirm_password")

        # Check if the old password is correct
        if not check_password(old_password, user.password):
            return Response({"error": "Old password is incorrect"}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the new password matches the confirm password
        if new_password != confirm_password:
            return Response({"error": "New passwords do not match"}, status=status.HTTP_400_BAD_REQUEST)

        # Set the new password
        user.set_password(new_password)
        user.save()

        return Response({"message": "Password updated successfully"}, status=status.HTTP_200_OK)

class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get the logged-in user
        user = request.user


        try:
            # Fetch the user_type and branch from the UserTypes model
            user_type_entry = UserTypes.objects.get(user=user)
            user_type = user_type_entry.user_type
            branch = user_type_entry.branch.name if user_type_entry.branch else None
        except UserTypes.DoesNotExist:
            return Response({"error": "User type not found"}, status=status.HTTP_404_NOT_FOUND)


        # Assuming you want to return some user profile fields
        profile_data = {
            "user_id":user.id,
            "email": user.email,
            "username": user.username,
            "contact_number": user.contact_number,
            "salary_details": user.salary_details,
            "user_type": user_type,
            "branch": branch
        }

        return Response(profile_data, status=status.HTTP_200_OK)




class SendOTPUserView(APIView):
    def post(self, request):
        serializer = OTPRequestUserSerializer(data=request.data)
        if serializer.is_valid():
            contact_number = serializer.validated_data['contact_number']
            otp = generate_otp(contact_number)
            send_otp_via_twilio(contact_number, otp)
            return Response({"message": "OTP sent successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyOTPUserView(APIView):
    def post(self, request):
        serializer = OTPVerifyUserSerializer(data=request.data)
        if serializer.is_valid():
            contact_number = serializer.validated_data['contact_number']
            otp = serializer.validated_data['otp']
            if verify_otp(contact_number, otp):
                try:
                    # Fetch the user associated with the contact number
                    user = CustomUser.objects.get(contact_number=contact_number)

                    # Fetch the user_type from the UserTypes model
                    user_type_record = UserTypes.objects.get(user=user)
                    user_type = user_type_record.user_type

                    # Create or get a token for the user
                    token, created = Token.objects.get_or_create(user=user)

                    return Response({
                        "message": "OTP verified successfully.",
                        "token": token.key,
                        "user_id": user.id,
                        "email": user.email,
                        "username": user.username,
                        "contact_number": user.contact_number,
                        "user_type": user_type
                    }, status=status.HTTP_200_OK)
                except CustomUser.DoesNotExist:
                    return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
                except UserTypes.DoesNotExist:
                    return Response({"error": "User type not found."}, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserUpdateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def patch(self, request, pk, *args, **kwargs):
        user = get_object_or_404(CustomUser, pk=pk)
        serializer = CustomUserUpdateSerializer(user, data=request.data, partial=True, context={'request': request})

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ManagerDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def delete(self, request, pk=None):
        # Ensure that only Admins can delete a Manager
        user = get_object_or_404(CustomUser, pk=pk)

        # Check if the user is a Manager
        user_type_instance = get_object_or_404(UserTypes, user=user)
        if user_type_instance.user_type != 'Manager':
            return Response(
                {'error': 'Only Managers can be deleted using this endpoint.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # If all checks pass, delete the Manager
        user.delete()
        return Response({'message': 'Manager deleted successfully'}, status=status.HTTP_200_OK)

class ListAdminsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request):
        admins = UserTypes.objects.filter(user_type='Admin')
        serializer = ListAdminManagerSerializer(admins, many=True)
        admins_count = admins.count()

        response_data = {
            'count': admins_count,  # Add the count field to the response
            'admins': serializer.data  # Include the serialized data for managers
        }

        return Response(response_data, status=200)

class ListManagersView(APIView):
    """
    View to list all Managers and their associated branch information.
    Accessible only to authenticated users.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        managers = UserTypes.objects.filter(user_type='Manager')
        serializer = ListAdminManagerSerializer(managers, many=True)
        manager_count = managers.count()

        response_data = {
            'count': manager_count,  # Add the count field to the response
            'managers': serializer.data  # Include the serialized data for managers
        }

        return Response( response_data, status=200)


class BranchCRUDView(APIView):
    """
    View to perform CRUD operations on Branches. Accessible only to Admins.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, pk=None):
        # Retrieve a specific branch or all branches
        if pk:
            branch = get_object_or_404(Branch, pk=pk)
            serializer = BranchSerializer(branch)
        else:
            branches = Branch.objects.all()
            serializer = BranchSerializer(branches, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        # Create a new branch
        serializer = BranchSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk=None):
        # Update an existing branch
        branch = get_object_or_404(Branch, pk=pk)
        serializer = BranchSerializer(branch, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk=None):
        # Delete a branch
        branch = get_object_or_404(Branch, pk=pk)
        branch.delete()
        return Response({'message': 'Branch deleted successfully'}, status=status.HTTP_200_OK)




class ContactAdminView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        try:
            user_type = UserTypes.objects.get(user=user).user_type
        except UserTypes.DoesNotExist:
            return Response({'message': 'User type not found.'}, status=status.HTTP_403_FORBIDDEN)

        if user_type != 'Manager':
            return Response({'message': 'Only Managers can contact the Admin.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = ContactAttemptSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            contact_attempt = serializer.save()

            # Attempt to notify the admin
            email_sent = self.notify_admin(contact_attempt)

            if email_sent:
                return Response({'message': 'Your message has been sent to the Admin.'}, status=status.HTTP_201_CREATED)
            else:
                return Response({'message': 'Failed to send the message to the Admin.'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def notify_admin(self, contact_attempt):
        try:
            send_mail(
                'New Contact Attempt by Manager',
                f"Manager {contact_attempt.user.username} sent the following message:\n\n{contact_attempt.message}",
                'balakrishnagujjeti9@gmail.com',
                [contact_attempt.admin.email],
                fail_silently=False,
            )
            # Create notification if email was successful
            Notification.objects.create(
                user=contact_attempt.admin,
                message=f"Manager {contact_attempt.user.username} sent a message: {contact_attempt.message}"
            )
            return True
        except (BadHeaderError, SMTPException):
            return False


class ListContactAttemptsView(APIView):
    """
    View to list all contact attempts sent to the logged-in Admin.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Check if the user is an Admin
        try:
            user_type = UserTypes.objects.get(user=user).user_type
        except UserTypes.DoesNotExist:
            return Response({'message': 'User type not found.'}, status=status.HTTP_403_FORBIDDEN)

        if user_type != 'Admin':
            return Response({'message': 'Only Admins can view contact attempts.'}, status=status.HTTP_403_FORBIDDEN)

        # Get contact attempts only for the logged-in admin
        contact_attempts = ContactAttempt.objects.filter(admin=user)
        serializer = ContactAttemptSerializer(contact_attempts, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


class AdminNotificationView(APIView):
    """
    View to list all notifications for a logged-in Admin and mark them as read.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Check if the user is an Admin
        try:
            user_type = UserTypes.objects.get(user=user).user_type
        except UserTypes.DoesNotExist:
            return Response({'message': 'User type not found.'}, status=status.HTTP_403_FORBIDDEN)

        if user_type != 'Admin':
            return Response({'message': 'Only Admins can view notifications.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            # Get notifications only for the logged-in admin
            notifications = Notification.objects.filter(user=user, is_read=False)
            # print("Number of unread notifications:", notifications.count())  # Debug print
            # print("Notifications retrieved:", notifications)  # Debug print

            if not notifications.exists():
                return Response({'message': 'No unread notifications.'}, status=status.HTTP_200_OK)

            serializer = NotificationSerializer(notifications, many=True)
            print("Serialized data:", serializer.data)  # Debug print

            # Mark notifications as read
            notifications.update(is_read=True)

            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



