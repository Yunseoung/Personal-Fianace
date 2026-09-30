import pandas as pd
from django.db.models import Sum
from django.http import JsonResponse
from .models import ExpenseRecord, Category # Category 모델 import 추가
from django.contrib.auth.models import User # User import
from django.db.models import F # F 객체 import
from datetime import datetime

# User ID=1을 사용하도록 설정 (Superuser)
def get_current_user():
    try:
        return User.objects.get(pk=1)
    except User.DoesNotExist:
        return None

def monthly_summary_api(request, year, month):
    request.user = get_current_user()
    if not request.user:
        return JsonResponse({'error': 'User not found'}, status=500)
    
    # 1. 사용자 필터링
    qs = ExpenseRecord.objects.filter(
        user=request.user, 
        date__year=year, 
        date__month=month
    )
    
    # 2. 분석: 카테고리별 합계 계산 (category__name 기준으로 그룹화)
    # None 카테고리(지출 기록 시 카테고리 미지정)를 "미지정"으로 처리
    summary = qs.values('category__name').annotate(
        category_name_display=F('category__name'), # 필드명을 명시적으로 사용
        total_amount=Sum('amount')
    ).order_by('-total_amount')
    
    # 3. 클라이언트 친화적인 JSON 응답
    data = {
        'total_expense': qs.aggregate(Sum('amount'))['amount__sum'] or 0,
        'categories': list(summary) # 카테고리별 이름과 총액 포함
    }
    return JsonResponse(data)

def time_series_api(request):
    request.user = get_current_user()
    if not request.user:
        return JsonResponse({'error': 'User not found'}, status=500)

    # 1. 필터링 (Query Parameters: start_date, end_date)
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    qs = ExpenseRecord.objects.filter(
        user=request.user, 
        date__range=[start_date, end_date]
    ).values('date').annotate(daily_total=Sum('amount')).order_by('date')
    
    # 2. JSON 응답
    data = {
        'labels': [item['date'].strftime('%Y-%m-%d') for item in qs],
        'data': [item['daily_total'] for item in qs]
    }
    return JsonResponse(data)

# 🌟🌟🌟 새로운 API: 미분류 상세 내역 조회 🌟🌟🌟
def unclassified_details_api(request, year, month):
    request.user = get_current_user()
    if not request.user:
        return JsonResponse({'error': 'User not found'}, status=500)
    
    try:
        # 1. '미분류' 카테고리 객체 찾기
        unclassified_category = Category.objects.get(name='미분류')
    except Category.DoesNotExist:
        return JsonResponse({'error': 'Unclassified category not found. Please create it in Admin page.'}, status=404)

    # 2. 미분류 항목만 필터링
    qs = ExpenseRecord.objects.filter(
        user=request.user,
        date__year=year,
        date__month=month,
        category=unclassified_category # 미분류 카테고리로 필터링
    ).values('date', 'amount', 'description').order_by('-date')

    # 3. JSON 응답 (날짜 객체를 직렬화 가능한 문자열로 변환)
    data = [{
        'date': item['date'].strftime('%Y-%m-%d'),
        'amount': item['amount'],
        'description': item['description']
    } for item in qs]
    
    return JsonResponse({'unclassified_records': data})