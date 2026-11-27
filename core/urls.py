from django.urls import path

from core import views

urlpatterns = [
    path('login/', views.ForumLoginView.as_view(), name='login'),
    path('logout/', views.logout, name='logout'),
    path('signup/', views.signup, name='signup'),
    path('profile/', views.profile, name='profile'),
]
