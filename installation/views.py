from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, PermissionDenied
from django.http import HttpResponse

from users.models import Branch
from users.serializers import BranchSerializer
from .models import VehicleInstallation
from .serializers import VehicleInstallationSerializer, RecentVehicleInstallationSerializer
from .utils import IsAdminUser, IsAdminOrManager
from django.db.models import Max
from users.models import UserTypes


class CreateInstallationView(APIView):
    """
    View to create a new Vehicle Installation. Only Admins can create installations.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        serializer = VehicleInstallationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UpdateInstallationView(APIView):
    """
    View to update an existing Vehicle Installation. Accessible to Admins and Managers.
    """
    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def patch(self, request, pk):
        try:
            installation = VehicleInstallation.objects.get(pk=pk)
        except VehicleInstallation.DoesNotExist:
            return Response({'message': f'Vehicle Installation with id {pk} not found'},
                            status=status.HTTP_404_NOT_FOUND)

        user = request.user

        try:
            user_type = UserTypes.objects.get(user=user).user_type
        except UserTypes.DoesNotExist:
            return Response({'message': 'User type not found.'}, status=status.HTTP_403_FORBIDDEN)

        if not self._has_permission(user_type, user, installation.branch):
            return Response({'message': 'You do not have permission to update this installation'},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = VehicleInstallationSerializer(installation, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _has_permission(self, user_type, user, branch):
        """
        Check if the user is an Admin or Manager for the specified branch.
        """
        if user_type == 'Admin':
            return True
        return UserTypes.objects.filter(user=user, user_type='Manager', branch=branch).exists()


class ListInstallationView(APIView):
    """
    View to list all Vehicle Installations. Accessible to Admins and Managers.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        try:
            user_type = UserTypes.objects.get(user=user).user_type
        except UserTypes.DoesNotExist:
            return Response({'message': 'User type not found.'}, status=status.HTTP_403_FORBIDDEN)

        if user_type == 'Admin':
            installations = VehicleInstallation.objects.all()
        else:
            # Ensure the user is a manager of the branch to filter installations
            branch_ids = UserTypes.objects.filter(user=user, user_type='Manager').values_list('branch', flat=True)
            installations = VehicleInstallation.objects.filter(branch__in=branch_ids)

        serializer = VehicleInstallationSerializer(installations, many=True)
        installation_count = installations.count()

        return Response({
            'count': installation_count,
            'installations': serializer.data
        }, status=status.HTTP_200_OK)


class DeleteInstallationView(APIView):
    """
    View to delete a Vehicle Installation. Accessible only to Admins.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def delete(self, request, pk):
        try:
            installation = VehicleInstallation.objects.get(pk=pk)
            installation.delete()
            return Response({'message': 'Vehicle Installation deleted successfully'}, status=status.HTTP_200_OK)
        except VehicleInstallation.DoesNotExist:
            return Response({'message': f'Vehicle Installation with given id:{pk} not found'},
                            status=status.HTTP_404_NOT_FOUND)


class RecentVehicleInstallationView(APIView):
    """
    View to get the most recently installed vehicle.
    """
    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request):
        # Get the most recently installed vehicle
        recent_vehicle = VehicleInstallation.objects.order_by('-datetime_installed').first()

        if recent_vehicle:
            serializer = RecentVehicleInstallationSerializer(recent_vehicle)
            return Response(serializer.data, status=200)
        else:
            return Response({'message': 'No vehicle installations found.'}, status=status.HTTP_404_NOT_FOUND)


class BranchWiseRecentVehicleInstallationView(APIView):
    """
    View to get the most recently installed vehicle for each branch.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        # Step 1: Get the most recent installation date for each branch
        recent_dates = VehicleInstallation.objects.values('branch').annotate(
            most_recent_date=Max('datetime_installed')
        ).values('branch', 'most_recent_date')

        # Step 2: Get the VehicleInstallation records for those recent dates
        recent_installations = VehicleInstallation.objects.filter(
            datetime_installed__in=[entry['most_recent_date'] for entry in recent_dates]
        ).order_by('branch', '-datetime_installed')

        # Step 3: Serialize and return the data
        serializer = RecentVehicleInstallationSerializer(recent_installations, many=True)
        return Response(serializer.data)


class BranchRecentVehicleInstallationView(APIView):
    """
    View to get the most recently installed vehicle for a specific branch, accessible only to managers of that branch.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, branch_id):
        """
        Retrieve the most recently installed vehicle for a specific branch if the user is a manager of that branch.
        """

        # Step 1: Validate branch_id
        if not VehicleInstallation.objects.filter(branch=branch_id).exists():
            raise NotFound(detail="Branch not found")

        # Step 2: Check if the user is a manager for the specified branch
        user = request.user
        if not UserTypes.objects.filter(user=user, user_type='Manager', branch=branch_id).exists():
            raise PermissionDenied(detail="You do not have permission to view this branch's installations.")

        # Step 3: Get the most recent installation date for the specified branch
        recent_date = VehicleInstallation.objects.filter(branch=branch_id).aggregate(
            most_recent_date=Max('datetime_installed')
        )['most_recent_date']

        if not recent_date:
            return Response({'message': 'No installations found for this branch'}, status=status.HTTP_404_NOT_FOUND)

        # Step 4: Get the VehicleInstallation record for the recent date
        recent_installation = VehicleInstallation.objects.filter(
            branch=branch_id, datetime_installed=recent_date
        ).first()

        if not recent_installation:
            return Response({'message': 'No recent installation found'}, status=status.HTTP_404_NOT_FOUND)

        # Step 5: Serialize and return the data
        serializer = RecentVehicleInstallationSerializer(recent_installation)
        return Response(serializer.data)
