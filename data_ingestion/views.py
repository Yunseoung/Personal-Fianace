import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from analysis.models import ExpenseRecord, Category
from django.contrib.auth.models import User
from datetime import datetime
from .forms import ExpenseForm, CSVUploadForm 

# User ID=1을 사용하도록 설정 (Superuser)
def get_current_user():
    try:
        return User.objects.get(pk=1)
    except User.DoesNotExist:
        return None

# 🌟🌟🌟 자동 분류 로직 함수 (KB 맞춤형으로 규칙 확장)
def categorize_expense(description):
    """지출 설명 텍스트를 기반으로 카테고리 이름을 반환합니다."""
    
    rules = {
        '페이머니': [
            '네이버페이', '카카오페이', '토스페이', '배민페이',
        ],
        '식비': [
            '씨유', '세븐일레븐', '지에스25', '이마트24', '빽다방', '다정식당', '까로치아', '파리바게뜨', '제임스타코',
            'CU편의점', 'GS25', '스타벅스', '김밥', '점심', '저녁', '식사', '마을회관', 
        ],
        '교통비': [
            '지하철', '버스', '고속버스', '택시', 'KOBUS', '코레일', 'Tmoney', '하이패스',
        ],
        '쇼핑/온라인': [
            '쿠팡', '무신사', 'APPLE', '에이블리코퍼레', 'G마켓', '옥션',
            '통신판매', '쇼핑몰', '온라인', '스팀', 
        ],
        '생활/취미': [
            '코인노래연습장', '위드코믹', '스토리피씨랩', '알파문구', '헤어바이리', '다이소', '올리브영',
            '병원', '약국', '헬스', '미용', '화장품', 'PC방',
        ],
        '구독/서비스': [
            '유튜브프리미엄', '쿠팡와우월회비', 'NETFLIX', 'SPOTIFY', '구독료',
        ],
        '주거/공과금': [
            '월세', '전기', '수도', '가스', '관리비',
        ],
    }
    
    desc_lower = description.lower()
    for category_name, keywords in rules.items():
        for keyword in keywords:
            if keyword.lower() in desc_lower:
                return category_name
                
    return "미분류"


# 지출 수기 입력 (CREATE/UPDATE)
def input_expense(request, record_id=None):
    request.user = get_current_user()
    if not request.user:
        messages.error(request, 'User가 존재하지 않습니다. createsuperuser를 실행해 주세요.')
        return redirect('admin:index') 

    if record_id:
        record = get_object_or_404(ExpenseRecord, pk=record_id, user=request.user)
    else:
        record = None

    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=record)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            expense.save()
            messages.success(request, f'지출 기록이 성공적으로 {"수정" if record_id else "저장"}되었습니다.')
            return redirect('dashboard:summary')
    else:
        form = ExpenseForm(instance=record)
        
    context = {'form': form, 'record': record}
    return render(request, 'data_ingestion/expense_form.html', context)


# 지출 삭제 (DELETE)
def delete_expense(request, record_id):
    request.user = get_current_user()
    if not request.user: return redirect('admin:index')

    record = get_object_or_404(ExpenseRecord, pk=record_id, user=request.user)
    if request.method == 'POST':
        record.delete()
        messages.success(request, '지출 기록이 삭제되었습니다.')
    
    return redirect('dashboard:summary') 


# CSV 파일 업로드
def upload_csv(request):
    request.user = get_current_user()
    if not request.user:
        messages.error(request, 'User가 존재하지 않습니다. createsuperuser를 실행해 주세요.')
        return redirect('admin:index')

    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            
            raw_data = csv_file.read()
            
            try:
                decoded_file = raw_data.decode('utf-8').splitlines()
            except UnicodeDecodeError:
                try:
                    decoded_file = raw_data.decode('euc-kr').splitlines()
                except UnicodeDecodeError:
                    messages.error(request, '파일 인코딩 오류가 발생했습니다. 파일을 UTF-8 또는 EUC-KR로 변환할 수 없습니다.')
                    return redirect('data_ingestion:upload')
            
            reader = csv.reader(decoded_file)
            
            for _ in range(5):
                try:
                    next(reader) 
                except StopIteration:
                    messages.error(request, '파일 내용이 너무 짧거나 형식이 올바르지 않습니다. 거래 내역이 5줄 미만입니다.')
                    return redirect('data_ingestion:upload')

            success_count = 0
            error_rows = []
            
            existing_categories = {c.name: c for c in Category.objects.all()}

            for row_index, row in enumerate(reader, 6): 
                try:
                    # 1. 날짜 필드가 비어있으면 건너뜀
                    if not row[0].strip():
                        continue
                        
                    # 2. '합계' 행 건너뜁니다.
                    if '합계' in "".join(row): 
                        continue

                    # 🌟 [수정됨] 취소 거래 필터링: 9번째 열 (Index 8) 사용
                    # 해당 열에 '취소'라는 단어가 포함되어 있으면 저장하지 않음
                    if len(row) > 8 and '취소' in row[8]:
                        continue
                        
                    # 🌟 [수정됨] 금액 필드: 5번째 열 (Index 4) 사용
                    amount_str = row[4].strip()

                    # 출금액이 비어있거나 '0'이면 입금 거래이므로 건너뜁니다.
                    if not amount_str or amount_str == '0':
                        continue
                        
                    cleaned_amount = amount_str.replace(',', '').replace('"', '').strip()
                    amount_value = int(cleaned_amount)

                    # 날짜 형식 변환
                    date_time_str = row[0].strip().split(' ')[0] 
                    date_obj = datetime.strptime(date_time_str, '%Y.%m.%d').date() 
                    final_date = date_obj.strftime('%Y-%m-%d') 
                    
                    # 설명 설정 (Index 2: 보낸분/받는분 필드)
                    description_text = row[2].strip() 

                    predicted_category_name = categorize_expense(description_text)
                    
                    if predicted_category_name not in existing_categories:
                        category, created = Category.objects.get_or_create(name=predicted_category_name)
                        existing_categories[predicted_category_name] = category
                    else:
                        category = existing_categories[predicted_category_name]

                    ExpenseRecord.objects.create(
                        user=request.user,
                        date=final_date, 
                        amount=amount_value,
                        category=category,
                        description=description_text
                    )
                    success_count += 1
                except Exception as e:
                    error_rows.append(f"행 {row_index}: {e} (데이터: {row})")
            
            if success_count > 0:
                 messages.success(request, f'{success_count}개의 지출 기록이 성공적으로 저장되었습니다. (자동 분류 적용)')
            if error_rows:
                 messages.error(request, f'{len(error_rows)}개의 기록 저장에 실패했습니다. 오류: {error_rows[0]} 등')
                 
            return redirect('dashboard:summary')
    else:
        form = CSVUploadForm()
    return render(request, 'data_ingestion/upload.html', {'form': form})