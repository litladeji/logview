from django.urls import path
from . import views

app_name = 'logviewer'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('logs/', views.logs_list, name='logs_list'),
    path('logs/<int:log_id>/', views.log_detail, name='log_detail'),
]