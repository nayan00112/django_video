# videos/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),                  # Homepage showing all videos
    path('upload/', views.upload_video, name='upload_video'),  # Video upload page
]
