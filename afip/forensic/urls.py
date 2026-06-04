from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('report/<int:audio_id>/', views.generate_report, name='report'),
    path('delete/<int:audio_id>/', views.delete_audio, name='delete_audio'),
]
