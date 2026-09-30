from django.db import models
from django.contrib.auth.models import User # Django 내장 User 모델 활용

class Category(models.Model):
    """지출 분류 (식비, 교통, 취미 등)"""
    name = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name

class ExpenseRecord(models.Model):
    """개인 지출 기록"""
    user = models.ForeignKey(User, on_delete=models.CASCADE) 
    
    date = models.DateField(db_index=True) # 날짜별 조회를 위해 인덱스 설정
    amount = models.IntegerField()
    
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    
    description = models.CharField(max_length=200, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True) 

    class Meta:
        ordering = ['-date'] # 최신 날짜순 정렬 기본 설정
