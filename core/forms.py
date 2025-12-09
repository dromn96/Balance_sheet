from django import forms
from .models import *
from django.contrib.auth import authenticate

class ExpensesForm(forms.ModelForm):
    date_created = forms.DateField(
        widget=forms.DateInput( attrs={'type': 'date'}),label='Дата расхода')
    class Meta:
        model = Expenses
        fields = '__all__'
        exclude = ('profile', )
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['month_name'].empty_label = 'Выберите месяц'
        self.fields['category_name'].empty_label = 'Без категории'
        self.fields['waste_name'].required = False

class HugeExpensesForm(forms.ModelForm):
    class Meta:
        model = HugeExpenses
        fields = '__all__'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category_name'].empty_label = 'Без категории'
        self.fields['text'].required = False

class IncomesForm(forms.ModelForm):
    date_created = forms.DateField(
        widget=forms.DateInput( attrs={'type': 'date'}),label='Дата дохода')
    class Meta:
        model = Income
        fields = '__all__'
        exclude = ('profile', )
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['month_name'].empty_label = 'Выберите месяц'
        self.fields['category_name'].empty_label = 'Без категории'
        self.fields['income_name'].required = False

class ExpensesCategoryForm(forms.ModelForm):
    class Meta:
        model = CategoryExpenses
        fields = '__all__'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category_name'].empty_label = 'без категории'
        self.fields['limit'].required = False

class IncomesCategoryForm(forms.ModelForm):
    class Meta:
        model = CategoryIncome
        fields = '__all__'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category_name'].empty_label = 'без категории'


