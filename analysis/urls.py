from django.urls import path
from . import views

app_name = 'analysis'

urlpatterns = [
    path('summary/<int:year>/<int:month>/', views.monthly_summary_api, name='monthly_summary'),
    path('timeseries/', views.time_series_api, name='time_series'),
    
    # 🌟🌟🌟 미분류 상세 조회 API 경로 추가 🌟🌟🌟
    path('unclassified/<int:year>/<int:month>/', views.unclassified_details_api, name='unclassified_details'),
]