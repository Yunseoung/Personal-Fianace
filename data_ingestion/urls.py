from django.urls import path
from . import views

app_name = 'data_ingestion'

urlpatterns = [
    # 수기 입력 (CREATE)
    path('input/', views.input_expense, name='input'),
    # 수정 (UPDATE)
    path('input/<int:record_id>/', views.input_expense, name='edit'), 
    # 삭제 (DELETE)
    path('delete/<int:record_id>/', views.delete_expense, name='delete'), 
    # CSV 업로드
    path('upload/', views.upload_csv, name='upload'),
]