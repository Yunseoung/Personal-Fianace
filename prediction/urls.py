from django.urls import path
from . import views

app_name = 'prediction'

urlpatterns = [
    # 기본 경로 (이번 달 보여줌)
    path('report/', views.prediction_report, name='report'),
    
    # 월 선택 경로 (예: /prediction/report/2025/10/)
    path('report/<int:year>/<int:month>/', views.prediction_report, name='report_month'),
]