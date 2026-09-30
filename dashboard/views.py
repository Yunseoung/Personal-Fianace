from django.shortcuts import render
from analysis.models import ExpenseRecord
from django.contrib.auth.models import User
from django.db.models import Sum
from django.db.models.functions import TruncDay, TruncMonth
import datetime
import calendar # 🌟 달력 날짜 계산을 위해 추가

def get_current_user():
    try:
        return User.objects.get(pk=1)
    except User.DoesNotExist:
        return None

def summary_view(request):
    user = get_current_user()
    if not user:
        return render(request, 'error_no_user.html')

    # 1. 월 목록 조회
    months_qs = ExpenseRecord.objects.filter(user=user) \
        .annotate(month_year=TruncMonth('date')) \
        .values('month_year') \
        .distinct() \
        .order_by('-month_year')
    
    available_months = []
    for m in months_qs:
        m_date = m['month_year']
        available_months.append({
            'year': m_date.year,
            'month': m_date.month,
            'label': f"{m_date.year}년 {m_date.month}월"
        })

    # 2. 조회할 연/월 결정
    selected_year = request.GET.get('year')
    selected_month = request.GET.get('month')

    if selected_year and selected_month:
        target_year = int(selected_year)
        target_month = int(selected_month)
    elif available_months:
        target_year = available_months[0]['year']
        target_month = available_months[0]['month']
    else:
        today = datetime.date.today()
        target_year = today.year
        target_month = today.month
    
    current_month_str = f"{target_year}-{target_month:02d}"

    # 3. 데이터 필터링
    expenses = ExpenseRecord.objects.filter(
        user=user, 
        date__year=target_year, 
        date__month=target_month
    )

    # 4. 총 지출
    total_spending = expenses.aggregate(Sum('amount'))['amount__sum'] or 0

    # 5. [왼쪽 차트] 3D 트리맵 데이터
    category_stats = expenses.values('category__name').annotate(total=Sum('amount')).order_by('-total')
    treemap_data = []
    category_table_data = []

    for item in category_stats:
        amount = int(item['total'])
        treemap_data.append({
            'category': item['category__name'],
            'amount': amount
        })
        percent = (amount / total_spending * 100) if total_spending > 0 else 0
        category_table_data.append({
            'name': item['category__name'],
            'amount': amount,
            'percent': round(percent, 1)
        })

    # 🌟 6. [오른쪽 차트] 일별 히트맵 데이터 (빈 날짜 0원으로 채우기)
    # (1) DB에서 지출이 있는 날짜만 가져와서 딕셔너리로 변환 {'2025-11-01': 5000, ...}
    daily_stats = expenses.annotate(day=TruncDay('date')).values('day').annotate(daily_total=Sum('amount')).order_by('day')
    daily_dict = {item['day'].strftime('%Y-%m-%d'): int(item['daily_total']) for item in daily_stats}
    
    # (2) 해당 월의 모든 날짜 생성 (1일 ~ 말일)
    heatmap_data = []
    # calendar.monthrange는 (시작요일, 마지막날짜)를 반환함
    _, last_day = calendar.monthrange(target_year, target_month)
    
    for day in range(1, last_day + 1):
        date_obj = datetime.date(target_year, target_month, day)
        date_str = date_obj.strftime('%Y-%m-%d')
        
        # 지출 내역이 있으면 그 값을, 없으면 0을 넣음
        amount = daily_dict.get(date_str, 0)
        heatmap_data.append([date_str, amount])

    # 7. 기타 데이터
    uncategorized_items = expenses.filter(category__name='미분류').order_by('-date')
    recent_expenses = expenses.order_by('-date')[:5]

    context = {
        'user': user,
        'current_month': current_month_str,
        'available_months': available_months,
        'total_spending': total_spending,
        'treemap_data': treemap_data,
        'heatmap_data': heatmap_data, # 0원이 포함된 전체 데이터
        'recent_expenses': recent_expenses,
        'category_table_data': category_table_data,
        'uncategorized_items': uncategorized_items,
        'target_year': target_year,
        'target_month': target_month,
    }

    return render(request, 'dashboard/summary.html', context)