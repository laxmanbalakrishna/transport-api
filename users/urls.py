from django.urls import path

from installation.views import RecentVehicleInstallationView
from .views import (UserRegistrationView, LoginView, BranchCRUDView, ListManagersView, ContactAdminView,
                    ListContactAttemptsView, AdminNotificationView, UserUpdateView, SendOTPUserView,
                    VerifyOTPUserView, LogoutView, ManagerDeleteView, ListAdminsView, ChangePasswordView, ProfileView)

urlpatterns = [
    path('register/',  UserRegistrationView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('profile-view/', ProfileView.as_view(), name='profile-view'),
    path('user/send-otp/', SendOTPUserView.as_view(), name='send_otp'),
    path('user/verify-otp/', VerifyOTPUserView.as_view(), name='verify_otp'),
    path('users/update/<uuid:pk>/', UserUpdateView.as_view(), name='user-update'),
    path('user/manager-delete/<uuid:pk>/',ManagerDeleteView.as_view(), name='delete-manager'),
    # URL pattern for listing all branches or creating a new branch
    path('branches/', BranchCRUDView.as_view(), name='branch-list-create'),

    # URL pattern for retrieving, updating, or deleting a specific branch by its primary key (pk)
    path('branches/<int:pk>/', BranchCRUDView.as_view(), name='branch-detail-update-delete'),
    path('managers/', ListManagersView.as_view(), name='list-managers'),
    path('admins/', ListAdminsView.as_view(), name='list-admins' ),
    path('recent-vehicle/', RecentVehicleInstallationView.as_view(), name='recent-vehicle-installation'),
    path('contact-admin/', ContactAdminView.as_view(), name='contact-admin'),
    path('admin-contact-attempts/', ListContactAttemptsView.as_view(), name='list-contact-attempts'),
    path('admin-notifications/', AdminNotificationView.as_view(), name='admin-notifications'),
]
