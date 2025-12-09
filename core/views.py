from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from datetime import datetime
from pprint import pprint
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Avg
from django.contrib.auth import login as login_func, logout as logout_func, get_user_model, authenticate
from collections import OrderedDict
from django.shortcuts import redirect
from django.http import HttpResponse, HttpResponseRedirect
from .models import *
from . forms import *
from . filter import *
from .services.expenses import get_expenses_by_category
from .services.incomes import get_incomes_by_category
from .services.excel import export_expenses, export_incomes

def main(request):
    year_list = Expenses.objects.values_list(
        'date_created__year', flat=True).distinct()
    if request.user.is_authenticated:
        profile = request.user.profile
    else:
        profile = None
    expense_list = Expenses.objects.all().filter(profile=profile)
    income_list = Income.objects.all().filter(profile=profile)
    category_list = CategoryExpenses.objects.all()
    month_list = Months.objects.all()

    year = request.GET.get('year', datetime.now().year)

    if not request.user.is_authenticated:
        return redirect('users/login')
    
    if not hasattr(request.user, 'profile'):
        return HttpResponse('нет профиля у пользователя')
    
    profile = request.user.profile
    expenses_by_category = get_expenses_by_category(profile=profile, year=year)
    incomes_by_category = get_incomes_by_category(profile=profile, year=year)

    # Общая сумма расходов за год
    total_expenses = expense_list.aggregate(total=Sum('cash_expenses'))['total'] or 0

    # Общая сумма доходов за год
    total_incomes = income_list.aggregate(total=Sum('amount'))['total'] or 0

    # Среднее значение расходов за год
    average_expenses = expense_list.aggregate(avg=Avg('cash_expenses'))['avg'] or 0

    # Среднее значение доходов за год
    average_incomes = income_list.aggregate(avg=Avg('amount'))['avg'] or 0

    # Сумма расходов по категориям для каждого месяца
    monthly_expenses = {}
    for month in month_list:
        total = expense_list.filter(month_name=month).aggregate(total=Sum('cash_expenses'))['total'] or 0
        monthly_expenses[month.month_name] = total

    # Сумма доходов по категориям для каждого месяца
    monthly_incomes = {}
    for month in month_list:
        total = income_list.filter(month_name=month).aggregate(total=Sum('amount'))['total'] or 0
        monthly_incomes[month.month_name] = total

    context = {'year_list': year_list, 'expense_list': expense_list, 'income_list': income_list, 'category_list': category_list, 'month_list': month_list, 'year': year}
    context.update({'selected_year': year})
    context.update({'expenses_by_category': expenses_by_category})
    context.update({'incomes_by_category': incomes_by_category})
    context.update({ 'total_expenses': total_expenses})
    context.update({'average_expenses': average_expenses})
    context.update({'monthly_expenses': monthly_expenses})
    context.update({ 'total_incomes': total_incomes})
    context.update({'average_incomes': average_incomes})
    context.update({'monthly_incomes': monthly_incomes})
    return render(request, 'main.html', context)


def incomes(request):
    year_list = Expenses.objects.values_list(
        'date_created__year', flat=True).distinct()
    profile = request.user.profile
    income_list = Income.objects.all().filter(profile=profile)
    category_list = CategoryIncome.objects.all()
    month_list = Months.objects.all()

    year = request.GET.get('year', datetime.now().year)
    category_id = request.GET.get('category')
    month_id = request.GET.get('month')

    if category_id:
        income_list = income_list.filter(
            category_name__category_place_on_the_list=category_id).filter(profile=profile)
        category_id = int(category_id)

    if month_id:
        income_list = income_list.filter(
            month_name__month_number=month_id, profile=profile)
        month_id = int(month_id)

    if year:
        income_list = income_list.filter(
            date_created__year=year, profile=profile)
        year = int(year)

    context = {'year_list': year_list, 'income_list': income_list, 'category_list': category_list,
               'month_list': month_list, 'category_id': category_id}
    return render(request, 'incomes.html', context)


def add_incomes(request):
    form = IncomesForm()
    if request.method == 'POST':
        form = IncomesForm(request.POST)
        if form.is_valid():
            income = form.save(commit=False)
            if request.user.is_authenticated:
                income.profile = request.user.profile
                income.save()
            return redirect('/incomes')
    context = {'form': form}
    return render(request, 'add_incomes.html', context)


def incomes_category(request):
    income_category_list = CategoryIncome.objects.all()
    context = {'income_category_list': income_category_list}
    return render(request, 'incomes_category.html', context)


def add_income_category(request):
    form = IncomesCategoryForm()
    if request.method == 'POST':
        form = IncomesCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/incomes/category')

    context = {'form': form}
    return render(request, 'add_income_category.html', context)


# @csrf_exempt
# def delete_income_category(request, income_id):
#     if request.method == 'POST':
#         expense = get_object_or_404(CategoryExpenses, pk=income_id)
#         expense.delete()
#         return JsonResponse({'status': 'success'})
#     else:
#         return JsonResponse({'status': 'fail'}, status=400)
#
#     return redirect('/incomes')


def edit_income(request, income_id):
    income = get_object_or_404(Income, id=income_id)
    form = IncomesForm(instance=income)

    if request.method == 'POST':
        form = IncomesForm(request.POST, instance=income)
        if form.is_valid():
            form.save()
            return redirect('/incomes')

    context = {'form': form}
    return render(request, 'edit_income.html', context)


@csrf_exempt
def delete_income(request, income_id):
    if request.method == 'POST':
        income = get_object_or_404(Income, pk=income_id)
        income.delete()
        return JsonResponse({'status': 'success'})
    else:
        return JsonResponse({'status': 'fail'}, status=400)
    return redirect('/incomes')


def export_incomes_to_excel(request):
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="incomes.xlsx"'
    wb = export_incomes()
    wb.save(response)
    return response


def expenses(request):
    year_list = Expenses.objects.values_list(
        'date_created__year', flat=True).distinct()
    profile = request.user.profile
    expenses_list = Expenses.objects.all().filter(profile=profile)
    category_list = CategoryExpenses.objects.all()
    month_list = Months.objects.all()

    year = request.GET.get('year', datetime.now().year)
    category_id = request.GET.get('category')
    month_id = request.GET.get('month')

    if category_id:
        expenses_list = expenses_list.filter(
            category_name__category_place_on_the_list=category_id, profile=profile)
        category_id = int(category_id)

    if month_id:
        expenses_list = expenses_list.filter(
            month_name__month_number=month_id, profile=profile)
        month_id = int(month_id)

    if year:
        expenses_list = expenses_list.filter(
            date_created__year=year, profile=profile)
        year = int(year)

    context = {'year_list': year_list, 'expenses_list': expenses_list, 'category_list': category_list,
               'month_list': month_list, 'category_id': category_id}
    return render(request, 'expenses.html', context)


def add_expenses(request):
    form = ExpensesForm()
    if request.method == 'POST':
        form = ExpensesForm(request.POST)
        if form.is_valid():
            exp = form.save(commit=False)
            if request.user.is_authenticated:
                exp.profile = request.user.profile
                exp.save()
            return redirect('/expenses')

    context = {'form': form}
    return render(request, 'add_expenses.html', context)


def expenses_category(request):
    expenses_category_list = CategoryExpenses.objects.all()

    context = {'expenses_category_list': expenses_category_list}
    return render(request, 'expenses_category.html', context)


def add_expenses_category(request):
    form = ExpensesCategoryForm()
    if request.method == 'POST':
        form = ExpensesCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/expenses/category')
    context = {'form': form}
    return render(request, 'add_expenses_category.html', context)


def edit_expense(request, expense_id):
    expense = get_object_or_404(Expenses, id=expense_id)
    form = ExpensesForm(instance=expense)

    if request.method == 'POST':
        form = ExpensesForm(request.POST, instance=expense)

        if form.is_valid():
            form.save()
            return redirect('/expenses')

    context = {'form': form}

    return render(request, 'edit_expense.html', context)


@csrf_exempt
def delete_expense(request, expense_id):
    if request.method == 'POST':
        expense = get_object_or_404(Expenses, pk=expense_id)
        expense.delete()
        return JsonResponse({'status': 'success'})
    else:
        return JsonResponse({'status': 'fail'}, status=400)
    return redirect('/expenses')

def export_expenses_to_excel(request):
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="expenses.xlsx"'
    wb = export_expenses()
    wb.save(response)
    return response

def huge_expenses(request):
    year_list = Expenses.objects.values_list(
        'date_created__year', flat=True).distinct()
    profile = request.user.profile
    huge_expenses_list = Expenses.objects.none()
    category_list = CategoryExpenses.objects.all()
    month_list = Months.objects.all()

    year = request.GET.get('year', datetime.now().year)
    category_id = request.GET.get('category')
    month_id = request.GET.get('month')



    for category in category_list:
        if HugeExpensesSettings.objects.filter(category=category).exists():
            amount_filter = HugeExpensesSettings.objects.get(
                category=category).amount
            data = Expenses.objects.filter(
                cash_expenses__gte=amount_filter, category_name=category, profile=profile)
            huge_expenses_list = huge_expenses_list.union(data)

    if category_id:
        huge_expenses_list = huge_expenses_list.filter(
            category_name__category_place_on_the_list=category_id, profile=profile)
        category_id = int(category_id)

    if month_id:
        huge_expenses_list = huge_expenses_list.filter(
            month_name__month_number=month_id, profile=profile)
        month_id = int(month_id)

    if year:
        huge_expenses_list = huge_expenses_list.filter(
            date_created__year=year, profile=profile)
        year = int(year)

    context = {'year_list': year_list,
               'huge_expenses_list': huge_expenses_list,
               'category_list': category_list,
               'month_list': month_list,
               }
    return render(request, 'huge_expenses.html', context)
