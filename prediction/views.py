import pandas as pd
import numpy as np
from django.shortcuts import render
from analysis.models import ExpenseRecord
from django.contrib.auth.models import User
from datetime import date, timedelta
from django.db.models import Sum
from django.db.models.functions import TruncMonth

def get_current_user():
    try:
        return User.objects.get(pk=1)
    except User.DoesNotExist:
        return None

def get_week_of_month(dt):
    return (dt.day - 1) // 7 + 1

def prediction_report(request, year=None, month=None):
    user = get_current_user()
    if not user:
        return render(request, 'error_no_user.html')

    today = date.today()
    real_current_month_str = today.strftime('%Y-%m')

    # 1. 날짜 설정
    if year is None or month is None:
        target_year = today.year
        target_month = today.month
    else:
        target_year = int(year)
        target_month = int(month)
    
    target_month_str = f"{target_year}-{target_month:02d}"

    # 지난달 구하기
    first_day_of_target = date(target_year, target_month, 1)
    last_day_of_prev = first_day_of_target - timedelta(days=1)
    prev_month_str = last_day_of_prev.strftime('%Y-%m')

    # 2. 전체 데이터 가져오기
    records = ExpenseRecord.objects.filter(user=user).values('date', 'amount', 'category__name')
    df = pd.DataFrame(list(records))
    
    if df.empty:
        return render(request, 'prediction/report.html', {'error': '분석할 데이터가 충분하지 않습니다.'})

    df['date'] = pd.to_datetime(df['date'])
    df['month_str'] = df['date'].dt.to_period('M').astype(str)
    df['week_num'] = df['date'].apply(get_week_of_month)

    # 3. 드롭다운 데이터
    months_qs = ExpenseRecord.objects.filter(user=user) \
        .annotate(month_year=TruncMonth('date')) \
        .values('month_year') \
        .annotate(c=Sum('amount')) \
        .order_by('-month_year')
    
    available_months = []
    for m in months_qs:
        m_date = m['month_year']
        available_months.append({
            'year': m_date.year,
            'month': m_date.month,
            'label': f"{m_date.year}년 {m_date.month}월"
        })

    # 4. [공통] 월별 집계
    monthly_sums = df.groupby('month_str')['amount'].sum().sort_index()
    
    # 최근 3개월 이동평균
    completed_months = monthly_sums[monthly_sums.index < real_current_month_str]
    moving_avg_3m = monthly_sums.rolling(window=3).mean().fillna(0).astype(int)
    completed_ma = moving_avg_3m[moving_avg_3m.index < real_current_month_str]

    if not completed_months.empty:
        last_3_avg = int(completed_months.tail(3).mean())
    else:
        last_3_avg = 0

    # 🌟 데이터 추출 범위를 5에서 10으로 수정
    recent_10_totals = completed_months.tail(10)
    recent_10_ma = completed_ma.tail(10)
    recent_months_labels = list(recent_10_totals.index.astype(str))
    recent_months_data = [int(x) for x in recent_10_totals.values]
    recent_ma_data = [int(x) for x in recent_10_ma.values]

    # 5. 스마트 예측 알고리즘
    past_data = completed_months
    ai_predicted_amount = 0
    prediction_method = ""
    safety_triggered = False
    
    if len(past_data) >= 1:
        last_n_values = past_data.tail(3).values
        n = len(last_n_values)
        has_trend = False
        if n >= 2:
            is_increasing = all(last_n_values[i] < last_n_values[i+1] for i in range(n-1))
            is_decreasing = all(last_n_values[i] > last_n_values[i+1] for i in range(n-1))
            has_trend = is_increasing or is_decreasing
        
        if has_trend and n >= 2:
            prediction_method = "📈 가중 선형 회귀 (트렌드 반영)"
            y = last_n_values
            X = np.arange(len(y))
            weights = np.linspace(1, 3, num=len(y))
            slope, intercept = np.polyfit(X, y, 1, w=weights)
            next_x = len(y)
            ai_predicted_amount = int(slope * next_x + intercept)
        else:
            if n == 1:
                prediction_method = "⚖️ 지난달 데이터 기준"
            else:
                prediction_method = f"⚖️ 이동 평균 (최근 {n}개월)"
            ai_predicted_amount = int(np.mean(last_n_values))
            
        last_month_amount = last_n_values[-1]
        if last_month_amount > 0 and ai_predicted_amount > 0:
            diff_ratio = abs(ai_predicted_amount - last_month_amount) / last_month_amount
            if diff_ratio >= 0.5:
                safety_triggered = True
                ai_predicted_amount = int(np.mean(last_n_values))
                prediction_method += " ➔ 🛡️ 안전장치"
    else:
        prediction_method = "데이터 부족"
        ai_predicted_amount = 0

    # 6. 현재 상태
    real_current_df = df[df['month_str'] == real_current_month_str]
    real_current_spending = int(real_current_df['amount'].sum()) if not real_current_df.empty else 0
    diff_real = last_3_avg - real_current_spending
    
    if diff_real > 0:
        real_status = "success"
        real_advice = f"아직 여유가 있습니다! 최근 3개월 평균보다 {diff_real:,}원 덜 사용했습니다."
    else:
        real_status = "danger"
        real_advice = f"경고: 최근 3개월 평균보다 {abs(diff_real):,}원 더 많이 사용했습니다! 절약이 필요합니다."

    # 7. [하단 변동] 주차별 지출 흐름
    target_df = df[df['month_str'] == target_month_str]
    target_month_total = 0
    
    weekly_filled = [0, 0, 0, 0, 0] 
    weekly_empty = [0, 0, 0, 0, 0]
    weekly_overflow = [0, 0, 0, 0, 0] # 초과분

    if not target_df.empty:
        target_month_total = int(target_df['amount'].sum())
        weekly_sums = target_df.groupby('week_num')['amount'].sum()
        
        remaining_water = real_current_spending
        
        for w in range(1, 6):
            bowl_size = int(weekly_sums.get(w, 0))
            if bowl_size == 0: continue

            if remaining_water >= bowl_size:
                weekly_filled[w-1] = bowl_size
                weekly_empty[w-1] = 0
                remaining_water -= bowl_size
            else:
                weekly_filled[w-1] = remaining_water
                weekly_empty[w-1] = bowl_size - remaining_water
                remaining_water = 0
        
        if remaining_water > 0:
            weekly_overflow[4] = remaining_water

    overflow_amount = sum(weekly_overflow)
    is_overflow = overflow_amount > 0

    context = {
        'prev_month_str': prev_month_str,
        'ai_predicted_amount': ai_predicted_amount,
        'prediction_method': prediction_method,
        'safety_triggered': safety_triggered,
        'recent_months_labels': recent_months_labels,
        'recent_months_data': recent_months_data,
        'recent_ma_data': recent_ma_data,
        'real_current_month': real_current_month_str,
        'real_current_spending': real_current_spending,
        'last_3_avg': last_3_avg,
        'real_diff_abs': abs(diff_real),
        'real_diff_is_positive': (diff_real > 0),
        'real_status': real_status,
        'real_advice': real_advice,
        'target_year': target_year,
        'target_month': target_month,
        'target_month_str': target_month_str,
        'target_month_total': target_month_total,
        'chart_labels': ['1주차', '2주차', '3주차', '4주차', '5주차'],
        'available_months': available_months,
        'weekly_filled': weekly_filled,
        'weekly_empty': weekly_empty,
        'weekly_overflow': weekly_overflow,
        'is_overflow': is_overflow,
        'overflow_amount': overflow_amount,
    }

    return render(request, 'prediction/report.html', context)