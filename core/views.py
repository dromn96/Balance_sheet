from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from datetime import datetime
from pprint import pprint
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum
from django.contrib.auth import login as login_func, logout as logout_func, get_user_model, authenticate
from collections import OrderedDict
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.crypto import constant_time_compare
from django.core.exceptions import ValidationError
from django.db import transaction
import json
from .models import *
from . forms import *
from . filter import *
from .services.expenses import get_expenses_by_category
from .services.incomes import get_incomes_by_category
from .services.excel import export_expenses, export_incomes
from .services.zen_csv_import import (
    import_records,
    parse_zen_csv,
    split_duplicate_records,
)
import secrets


MAX_IMPORT_FILE_SIZE = 5 * 1024 * 1024

# Обработка формы - из даты берется месяц и добавляется в БД
def _assign_month_from_date(form):
    month = Months.objects.filter(
        month_number=form.cleaned_data['date_created'].month
    ).first()
    if month is None:
        form.add_error(
            'date_created',
            'В справочнике месяцев нет месяца для выбранной даты.',
        )
        return False
    form.instance.month_name = month
    return True


def main(request):
    current_year = datetime.now().year
    year_list = list(Expenses.objects.values_list(
        'date_created__year', flat=True).distinct())
    if current_year not in year_list:
        year_list.append(current_year)
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
    else:
        profile = None
    expense_list = Expenses.objects.all().filter(profile=profile)
    income_list = Income.objects.all().filter(profile=profile)
    category_list = CategoryExpenses.objects.all()
    month_list = Months.objects.all()

    year = int(request.GET.get('year') or current_year)
    expense_list = expense_list.filter(date_created__year=year)
    income_list = income_list.filter(date_created__year=year)

    if not request.user.is_authenticated:
        return redirect('users/login')
    
    if profile is None:
        return HttpResponse('нет профиля у пользователя')
    
    profile = request.user.profile
    expenses_by_category = get_expenses_by_category(profile=profile, year=year)
    incomes_by_category = get_incomes_by_category(profile=profile, year=year)

    # Общая сумма расходов за год
    total_expenses = expense_list.aggregate(total=Sum('cash_expenses'))['total'] or 0

    # Общая сумма доходов за год
    total_incomes = income_list.aggregate(total=Sum('amount'))['total'] or 0

    # Сумма значений «Среднее факт» по категориям
    sum_average_expenses = sum(
        (data['average'] for data in expenses_by_category.values()), 0
    )
    sum_average_incomes = sum(
        (data['average'] for data in incomes_by_category.values()), 0
    )
    sum_planned_expenses = sum(
        (data['planned_average'] or 0 for data in expenses_by_category.values()),
        0,
    )
    sum_planned_incomes = sum(
        (data['planned_average'] or 0 for data in incomes_by_category.values()),
        0,
    )

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
    context.update({'sum_planned_expenses': sum_planned_expenses})
    context.update({'sum_average_expenses': sum_average_expenses})
    context.update({'monthly_expenses': monthly_expenses})
    context.update({ 'total_incomes': total_incomes})
    context.update({'sum_planned_incomes': sum_planned_incomes})
    context.update({'sum_average_incomes': sum_average_incomes})
    context.update({'monthly_incomes': monthly_incomes})
    pending_import = request.session.get('pending_transaction_import')
    if pending_import and pending_import.get('profile_id') == profile.pk:
        context['pending_import'] = {
            'token': pending_import['token'],
            'duplicate_count': pending_import['duplicate_count'],
        }
    return render(request, 'main.html', context)


@login_required
def save_category_plans(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        payload = json.loads(request.body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({'error': 'Некорректный формат данных.'}, status=400)

    if not isinstance(payload, dict):
        return JsonResponse({'error': 'Некорректный формат данных.'}, status=400)

    updates = []
    for key, model in (
        ('expenses', CategoryExpenses),
        ('incomes', CategoryIncome),
    ):
        records = payload.get(key)
        if not isinstance(records, list):
            return JsonResponse({'error': 'Некорректный список категорий.'}, status=400)

        parsed_records = []
        seen_ids = set()
        for record in records:
            if not isinstance(record, dict):
                return JsonResponse({'error': 'Некорректные данные категории.'}, status=400)
            category_id = record.get('id')
            value = record.get('value')
            if (
                isinstance(category_id, bool)
                or not isinstance(category_id, int)
                or category_id <= 0
                or category_id in seen_ids
                or isinstance(value, bool)
            ):
                return JsonResponse({'error': 'Некорректные данные категории.'}, status=400)
            seen_ids.add(category_id)

            try:
                cleaned_value = (
                    None if value is None or value == ''
                    else model._meta.get_field('planned_average').clean(value, None)
                )
            except ValidationError:
                return JsonResponse(
                    {
                        'error': (
                            'Плановая сумма должна быть числом не более чем '
                            'с двумя знаками после запятой.'
                        )
                    },
                    status=400,
                )

            parsed_records.append((category_id, cleaned_value))

        categories = model.objects.in_bulk(seen_ids)
        if len(categories) != len(seen_ids):
            return JsonResponse({'error': 'Одна или несколько категорий не найдены.'}, status=400)
        updates.extend(
            (categories[category_id], value)
            for category_id, value in parsed_records
        )

    with transaction.atomic():
        for category, value in updates:
            category.planned_average = value
            category.save(update_fields=['planned_average'])

    return JsonResponse({'saved': len(updates)})


# Импорт транзакций из CSV-файла, загруженного пользователем. Поддерживается подтверждение импорта при обнаружении дубликатов.
@login_required(login_url='login')
def import_transactions(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    profile = getattr(request.user, 'profile', None)
    if profile is None:
        messages.error(request, 'У пользователя не создан профиль.')
        return redirect('/')

    action = request.POST.get('action')
    pending_import = request.session.get('pending_transaction_import')

    if action in {'continue', 'cancel'}:
        token = request.POST.get('token', '')
        if (
            not pending_import
            or pending_import.get('profile_id') != profile.pk
            or not constant_time_compare(pending_import.get('token', ''), token)
        ):
            messages.error(request, 'Подтверждение импорта устарело. Загрузите файл ещё раз.')
            return redirect('/')

        if action == 'cancel':
            del request.session['pending_transaction_import']
            messages.info(request, 'Импорт отменён.')
            return redirect('/')

        records = pending_import['records']
        del request.session['pending_transaction_import']
        try:
            expense_count, income_count, duplicate_count = import_records(
                profile, records
            )
        except ValueError as error:
            messages.error(request, str(error))
            return redirect('/')
        messages.success(
            request,
            f'Импорт завершён: расходов — {expense_count}, '
            f'доходов — {income_count}, пропущено совпадений — {duplicate_count}.',
        )
        return redirect('/')

    if action != 'upload':
        messages.error(request, 'Неизвестное действие импорта.')
        return redirect('/')

    request.session.pop('pending_transaction_import', None)
    uploaded_file = request.FILES.get('csv_file')
    if uploaded_file is None:
        messages.error(request, 'Выберите CSV-файл для импорта.')
        return redirect('/')
    if uploaded_file.size > MAX_IMPORT_FILE_SIZE:
        messages.error(request, 'Размер CSV-файла не должен превышать 5 МБ.')
        return redirect('/')
    if not uploaded_file.name.lower().endswith('.csv'):
        messages.error(request, 'Для импорта выберите файл с расширением .csv.')
        return redirect('/')

    try:
        records = parse_zen_csv(uploaded_file)
        _, existing_duplicate_count, _ = split_duplicate_records(profile, records)
        if existing_duplicate_count > 5:
            pending_import = {
                'token': secrets.token_urlsafe(24),
                'profile_id': profile.pk,
                'duplicate_count': existing_duplicate_count,
                'records': records,
            }
            request.session['pending_transaction_import'] = pending_import
            return redirect('/')

        expense_count, income_count, duplicate_count = import_records(
            profile, records
        )
    except ValueError as error:
        messages.error(request, str(error))
        return redirect('/')

    messages.success(
        request,
        f'Импорт завершён: расходов — {expense_count}, доходов — {income_count}, '
        f'пропущено совпадений — {duplicate_count}.',
    )
    return redirect('/')


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
        if form.is_valid() and _assign_month_from_date(form):
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
        if form.is_valid() and _assign_month_from_date(form):
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
        if form.is_valid() and _assign_month_from_date(form):
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

        if form.is_valid() and _assign_month_from_date(form):
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
