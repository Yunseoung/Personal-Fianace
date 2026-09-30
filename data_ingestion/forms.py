from django import forms
from analysis.models import ExpenseRecord, Category

class ExpenseForm(forms.ModelForm):
    # DateField 오버라이드 및 help_text 추가
    date = forms.DateField(
        label='Date',
        input_formats=['%Y-%m-%d', '%y.%m.%d', '%Y.%m.%d', '%m/%d/%Y'],
        widget=forms.DateInput(attrs={'placeholder': 'YYYY-MM-DD 또는 YY.MM.DD'}),
        help_text='입력 가능한 형식: YYYY-MM-DD (예: 2025-10-26) 또는 YY.MM.DD (예: 25.10.26)'
    )
    
    # Amount 필드 추가 및 help_text 적용
    amount = forms.IntegerField(
        label='Amount',
        help_text='지출 금액을 숫자만 사용하여 입력하세요 (예: 12000). 쉼표(,)는 입력하지 마세요.'
    )
    
    # Description 필드
    description = forms.CharField(
        max_length=200, 
        required=False,
        help_text='지출 내역이나 사용처를 간략하게 입력하세요.'
    )
    
    # 수기 입력 폼 정의
    class Meta:
        model = ExpenseRecord
        fields = ['date', 'amount', 'category', 'description']

class CSVUploadForm(forms.Form):
    """CSV 파일 업로드 전용 폼"""
    csv_file = forms.FileField(label='CSV 파일 선택')