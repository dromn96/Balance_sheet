import json
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from core.models import (
    CategoryExpenses,
    CategoryIncome,
    Expenses,
    Income,
    Months,
    Profile,
)
from core.services.zen_csv_import import parse_zen_csv


class ZenCsvImportTests(SimpleTestCase):
    def test_parses_metadata_decimal_amounts_and_both_transaction_types(self):
        content = (
            'zm_dump_2011,1793789242,,,"4,0",\n'
            '\n'
            'date,categoryName,payee,comment,outcomeAccountName,outcome,'
            'outcomeCurrencyShortTitle,incomeAccountName,income,'
            'incomeCurrencyShortTitle,createdDate,changedDate\n'
            '2026-10-01,Продукты,Магнит,Покупка,Alpha Pay,"448,00",RUB,,,,,\n'
            '2026-10-02,Кэшбэк,,Возврат,,,,Alpha Pay,"864,61",RUB,,\n'
        ).encode('utf-8')
        uploaded_file = SimpleUploadedFile('transactions.csv', content)

        records = parse_zen_csv(uploaded_file)

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0], {
            'kind': 'expense',
            'date': '2026-10-01',
            'amount': '448.00',
            'category': 'Продукты',
            'description': 'Покупка',
            'payee': 'Магнит',
            'account_name': 'Alpha Pay',
            'currency': 'RUB',
        })
        self.assertEqual(records[1], {
            'kind': 'income',
            'date': '2026-10-02',
            'amount': '864.61',
            'category': 'Кэшбэк',
            'description': 'Возврат',
            'payee': '',
            'account_name': 'Alpha Pay',
            'currency': 'RUB',
        })

    def test_rejects_rows_with_both_income_and_expense(self):
        content = (
            'date,categoryName,payee,comment,outcomeAccountName,outcome,'
            'outcomeCurrencyShortTitle,incomeAccountName,income,'
            'incomeCurrencyShortTitle\n'
            '2026-10-01,,,,Alpha Pay,"10,00",RUB,Alpha Pay,"10,00",RUB\n'
        ).encode('utf-8')
        uploaded_file = SimpleUploadedFile('transactions.csv', content)

        with self.assertRaisesRegex(ValueError, 'одновременно указаны расход и доход'):
            parse_zen_csv(uploaded_file)


class CategoryPlanTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='plan-editor',
            password='test-password',
        )
        self.profile = Profile.objects.create(user=self.user)
        self.expense_category = CategoryExpenses.objects.create(
            category_name='Продукты',
            category_place_on_the_list=1,
        )
        self.income_category = CategoryIncome.objects.create(
            category_name='Зарплата',
            category_place_on_the_list=1,
        )
        self.client.force_login(self.user)
        self.url = reverse('save_category_plans')

    def test_saves_expense_and_income_plans(self):
        response = self.client.post(
            self.url,
            data=json.dumps({
                'expenses': [{'id': self.expense_category.pk, 'value': '12500.50'}],
                'incomes': [{'id': self.income_category.pk, 'value': '85000'}],
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.expense_category.refresh_from_db()
        self.income_category.refresh_from_db()
        self.assertEqual(str(self.expense_category.planned_average), '12500.50')
        self.assertEqual(str(self.income_category.planned_average), '85000.00')

    def test_rejects_invalid_plan_without_saving_any_categories(self):
        response = self.client.post(
            self.url,
            data=json.dumps({
                'expenses': [{'id': self.expense_category.pk, 'value': '12500.50'}],
                'incomes': [{'id': self.income_category.pk, 'value': 'not-a-number'}],
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.expense_category.refresh_from_db()
        self.assertIsNone(self.expense_category.planned_average)

    def test_main_displays_saved_plans_for_both_category_types(self):
        self.expense_category.planned_average = '12500.50'
        self.expense_category.save()
        self.income_category.planned_average = '85000.00'
        self.income_category.save()

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Среднее план')
        self.assertContains(response, 'data-value="12500.50"')
        self.assertContains(response, 'data-value="85000.00"')
        self.assertContains(response, 'id="csrf-token"')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')

    def test_summary_fact_average_totals_sum_category_averages(self):
        second_expense_category = CategoryExpenses.objects.create(
            category_name='Транспорт',
            category_place_on_the_list=2,
        )
        second_income_category = CategoryIncome.objects.create(
            category_name='Премия',
            category_place_on_the_list=2,
        )
        january = Months.objects.create(month_name='Январь', month_number=1)
        transaction_date = date(date.today().year, 1, 1)

        Expenses.objects.create(
            profile=self.profile,
            category_name=self.expense_category,
            month_name=january,
            date_created=transaction_date,
            cash_expenses=30,
        )
        Expenses.objects.create(
            profile=self.profile,
            category_name=second_expense_category,
            month_name=january,
            date_created=transaction_date,
            cash_expenses=60,
        )
        Income.objects.create(
            profile=self.profile,
            category_name=self.income_category,
            month_name=january,
            date_created=transaction_date,
            amount=100,
        )
        Income.objects.create(
            profile=self.profile,
            category_name=second_income_category,
            month_name=january,
            date_created=transaction_date,
            amount=300,
        )

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['sum_average_expenses'], Decimal('90'))
        self.assertEqual(response.context['sum_average_incomes'], Decimal('400'))

    def test_summary_planned_totals_sum_category_plans(self):
        second_expense_category = CategoryExpenses.objects.create(
            category_name='Транспорт',
            category_place_on_the_list=2,
            planned_average=Decimal('5.75'),
        )
        second_income_category = CategoryIncome.objects.create(
            category_name='Премия',
            category_place_on_the_list=2,
            planned_average=Decimal('250.00'),
        )
        self.expense_category.planned_average = Decimal('10.25')
        self.expense_category.save()
        self.income_category.planned_average = Decimal('1000.00')
        self.income_category.save()

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['sum_planned_expenses'], Decimal('16.00'))
        self.assertEqual(response.context['sum_planned_incomes'], Decimal('1250.00'))
