"""
URL configuration for personal_finance project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from dashboard.views import summary_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', summary_view, name='index'),

    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('ingest/', include('data_ingestion.urls', namespace='data_ingestion')),
    path('api/analysis/', include('analysis.urls', namespace='analysis')),
    # 🌟 예측 앱 URL 추가
    path('prediction/', include('prediction.urls', namespace='prediction')),
]