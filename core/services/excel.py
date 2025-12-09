import openpyxl
from django.http import HttpResponse
from core.models import *

def export_expenses():
    exps = Expenses.objects.all()
    columns = ['Месяц', 'Категория', 'Расход', 'Дата создания', 'Наименования']

    wb = openpyxl.Workbook()
    ws = wb.active

    ws.title = 'Расходы'

    ws.append(columns)

    for exp in exps:
        ws.append([exp.month_name.month_name, exp.category_name.category_name, exp.cash_expenses, exp.date_created, exp.waste_name])

    return wb


def export_incomes():
    incs = Income.objects.all()
    columns = ['Месяц', 'Категория', 'Расход', 'Дата создания', 'Наименования']

    wb = openpyxl.Workbook()
    ws = wb.active

    ws.title = 'Доходы'

    ws.append(columns)

    for inc in incs:
        ws.append([inc.month_name.month_name, inc.category_name.category_name, inc.amount, inc.date_created, inc.income_name])

    return wb



