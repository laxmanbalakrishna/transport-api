from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework import status

from users.models import UserTypes


class IsAdminUser(BasePermission):
    """
    Custom permission to only allow Admin users to perform certain actions.
    """
    def has_permission(self, request, view):
        # Check if the user is authenticated and has 'Admin' user type
        if not request.user.is_authenticated:
            return False
        try:
            user_type = UserTypes.objects.get(user=request.user).user_type
        except UserTypes.DoesNotExist:
            return False
        return user_type == 'Admin'

class IsAdminOrManager(BasePermission):
    """
    Custom permission to allow only Admins and Managers to perform certain actions.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        try:
            user_type = UserTypes.objects.get(user=request.user).user_type
        except UserTypes.DoesNotExist:
            return False
        return user_type in ['Admin', 'Manager']
