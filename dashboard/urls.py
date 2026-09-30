from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # 메인 대시보드 페이지
    path('', views.summary_view, name='summary'),
]