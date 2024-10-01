from django.urls import path

from .views import (
    CreateInstallationView,
    UpdateInstallationView,
    ListInstallationView,
    DeleteInstallationView, RecentVehicleInstallationView, BranchRecentVehicleInstallationView,
    BranchWiseRecentVehicleInstallationView, SendOTPView, VerifyOTPView, compare_branch_outputs, LogoutView,
    ListInstallationInstalledUserView, InstalledUserProfileView
)

urlpatterns = [
    path('installations/create/', CreateInstallationView.as_view(), name='create-installation'),
    path('installations/update/<int:pk>/', UpdateInstallationView.as_view(), name='update-installation'),
    path('installations/', ListInstallationView.as_view(), name='list-installations'),
    path('installations/installedUser/', ListInstallationInstalledUserView.as_view(), name='list-installations-installedUser'),
    path('installations/installedUser/profile-view/', InstalledUserProfileView.as_view(), name='profile-view-installedUser'),
    path('installations/delete/<int:pk>/', DeleteInstallationView.as_view(), name='delete-installation'),
    path('installations/send-otp/', SendOTPView.as_view(), name='send_otp'),
    path('installations/verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('installations/logout/', LogoutView.as_view(), name='logout'),
    path('installations/recent-vehicle/', RecentVehicleInstallationView.as_view(), name='recent-vehicle-installation'),
    path('installations/branch-wise-recent-vehicle/', BranchWiseRecentVehicleInstallationView.as_view(),
         name='branch-wise-recent-vehicle-installation'),
    path('installations/recent-installation/<int:branch_id>/', BranchRecentVehicleInstallationView.as_view(), name='branch-recent-installation'),
    path('installations/compare-output/', compare_branch_outputs, name='compare-branch-output'),
]



