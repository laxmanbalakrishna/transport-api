from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model, authenticate
from .serializers import CustomUserSerializer, LoginSerializer, BranchSerializer, ManagerSerializer, \
    ContactAttemptSerializer, NotificationSerializer
from .models import UserTypes, Branch, ContactAttempt, CustomUser, Notification
from rest_framework.authtoken.models import Token
from installation.utils import IsAdminUser, IsAdminOrManager
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail


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
                        "user_type": user_type_instance.user_type if user_type_instance else None,
                        "branch": user_type_instance.branch.name if user_type_instance and user_type_instance.branch else None
                    }, status=status.HTTP_200_OK)
            except UserModel.DoesNotExist:
                pass

            return Response({"non_field_errors": ["Invalid email or password."]}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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


class ListManagersView(APIView):
    """
    View to list all Managers and their associated branch information.
    Accessible only to authenticated users.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        managers = UserTypes.objects.filter(user_type='Manager')
        serializer = ManagerSerializer(managers, many=True)
        return Response(serializer.data, status=200)


class ContactAdminView(APIView):
    """
    View to allow Managers to contact the Admin.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        # Check if the user is a Manager
        try:
            user_type = UserTypes.objects.get(user=user).user_type
        except UserTypes.DoesNotExist:
            return Response({'message': 'User type not found.'}, status=status.HTTP_403_FORBIDDEN)

        if user_type != 'Manager':
            return Response({'message': 'Only Managers can contact the Admin.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = ContactAttemptSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            contact_attempt = serializer.save()

            # Notify the specific admin
            self.notify_admin(contact_attempt)

            return Response({'message': 'Your message has been sent to the Admin.'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def notify_admin(self, contact_attempt):

        # Create a notification for the specific admin
        Notification.objects.create(
            user=contact_attempt.admin,
            message=f"Manager {contact_attempt.user.username} sent a message: {contact_attempt.message}"
        )

        # Send an email to the specific admin
        send_mail(
            'New Contact Attempt by Manager',
            f"Manager {contact_attempt.user.username} sent the following message:\n\n{contact_attempt.message}",
            'from@example.com',
            [contact_attempt.admin.email]
        )


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
    View to list all notifications for an logged-in Admin and mark them as read.
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

        # Get notifications only for the logged-in admin
        notifications = Notification.objects.filter(user=user, is_read=False)
        serializer = NotificationSerializer(notifications, many=True)

        # Mark notifications as read
        notifications.update(is_read=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
