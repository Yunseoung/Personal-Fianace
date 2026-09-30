from django.contrib import admin
from .models import ExpenseRecord, Category

# ExpenseRecord 모델 등록
@admin.register(ExpenseRecord)
class ExpenseRecordAdmin(admin.ModelAdmin):
    list_display = ('date', 'amount', 'category', 'user', 'description')
    list_filter = ('category', 'user')
    search_fields = ('description', 'user__username')
    date_hierarchy = 'date'

# 🌟 Category 모델을 관리자 페이지에 등록
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)