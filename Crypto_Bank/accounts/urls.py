from django.urls import path
from .views import UserRegistrationView, UserLoginView, UserLogoutView, UserProfileUpdateView

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/',  UserLoginView.as_view(), name='login'),
    path('logout/',  UserLogoutView.as_view(), name='logout'),
    path('profile/', UserProfileUpdateView.as_view(), name='profile'),
]