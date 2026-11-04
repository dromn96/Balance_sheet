import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation

from django.db import transaction

from core.models import (
    CategoryExpenses,
    CategoryIncome,
    Expenses,
    Income,
    Months,
)


MAX_AMOUNT_DIGITS = 12
MAX_AMOUNT_DECIMAL_PLACES = 2
REQUIRED_COLUMNS = {
    'date',
    'categoryName',
    'payee',
    'comment',
    'outcomeAccountName',
    'incomeAccountName',
    'outcome',
    'outcomeCurrencyShortTitle',
    'income',
    'incomeCurrencyShortTitle',
}


def parse_zen_csv(uploaded_file):
    try:
        contents = uploaded_file.read().decode('utf-8-sig')
    except UnicodeDecodeError as error:
        raise ValueError('Файл должен быть сохранён в кодировке UTF-8.') from error

    reader = csv.reader(io.StringIO(contents, newline=''))
    header = None
    header_line = None
    for line_number, row in enumerate(reader, start=1):
        if row and row[0].strip() == 'date':
            header = [column.strip() for column in row]
            header_line = line_number
            break
    if header is None:
        raise ValueError('Не найдена строка заголовков CSV с колонкой date.')

    missing_columns = REQUIRED_COLUMNS - set(header)
    if missing_columns:
        raise ValueError(
            'В CSV отсутствуют обязательные колонки: '
            + ', '.join(sorted(missing_columns))
        )

    records = []
    for line_number, row in enumerate(reader, start=header_line + 1):
        if not row or all(not value.strip() for value in row):
            continue
        if len(row) != len(header):
            raise ValueError(f'Строка {line_number}: неверное количество колонок.')

        values = {column: value.strip() for column, value in zip(header, row)}
        outcome = values['outcome']
        income = values['income']
        if not outcome and not income:
            continue
        if outcome and income:
            raise ValueError(
                f'Строка {line_number}: одновременно указаны расход и доход.'
            )

        try:
            transaction_date = date.fromisoformat(values['date'])
        except ValueError as error:
            raise ValueError(f'Строка {line_number}: неверная дата.') from error

        amount_value = outcome or income
        try:
            amount = Decimal(amount_value.replace(',', '.'))
        except InvalidOperation as error:
            raise ValueError(f'Строка {line_number}: неверная сумма.') from error
        if not amount.is_finite():
            raise ValueError(f'Строка {line_number}: сумма должна быть конечной.')
        decimal_places = max(-amount.as_tuple().exponent, 0)
        integer_digits = max(amount.adjusted() + 1, 0) if amount else 1
        if (
            decimal_places > MAX_AMOUNT_DECIMAL_PLACES
            or integer_digits > MAX_AMOUNT_DIGITS - MAX_AMOUNT_DECIMAL_PLACES
        ):
            raise ValueError(f'Строка {line_number}: сумма превышает допустимую точность.')

        records.append({
            'kind': 'expense' if outcome else 'income',
            'date': transaction_date.isoformat(),
            'amount': str(amount),
            'category': values['categoryName'],
            'description': values['comment'],
            'payee': values['payee'],
            'account_name': (
                values['outcomeAccountName']
                if outcome
                else values['incomeAccountName']
            ),
            'currency': (
                values['outcomeCurrencyShortTitle']
                if outcome
                else values['incomeCurrencyShortTitle']
            ),
        })

    if not records:
        raise ValueError('В CSV не найдено ни одной операции с суммой.')
    return records


def _record_key(record):
    return (
        record['kind'],
        date.fromisoformat(record['date']),
        Decimal(record['amount']),
        record['description'],
    )


def _existing_keys(profile, records):
    dates = [date.fromisoformat(record['date']) for record in records]
    date_range = (min(dates), max(dates))
    keys = {
        ('expense', transaction_date, amount, description)
        for transaction_date, amount, description in Expenses.objects.filter(
            profile=profile,
            date_created__range=date_range,
        ).values_list('date_created', 'cash_expenses', 'waste_name')
    }
    keys.update(
        ('income', transaction_date, amount, description)
        for transaction_date, amount, description in Income.objects.filter(
            profile=profile,
            date_created__range=date_range,
        ).values_list('date_created', 'amount', 'income_name')
    )
    return keys


def split_duplicate_records(profile, records):
    existing = _existing_keys(profile, records)
    seen = set(existing)
    new_records = []
    existing_duplicate_count = 0
    duplicate_count = 0
    for record in records:
        key = _record_key(record)
        if key in seen:
            duplicate_count += 1
            if key in existing:
                existing_duplicate_count += 1
        else:
            new_records.append(record)
            seen.add(key)
    return new_records, existing_duplicate_count, duplicate_count


def _get_or_create_category(category_model, category_name):
    normalized_name = category_name.strip().casefold()
    if not normalized_name:
        return None

    for category in category_model.objects.all():
        if category.category_name.strip().casefold() == normalized_name:
            return category

    order = (
        category_model.objects.order_by('-category_place_on_the_list')
        .values_list('category_place_on_the_list', flat=True)
        .first()
        or 0
    )
    return category_model.objects.create(
        category_name=category_name.strip(),
        category_place_on_the_list=order + 1,
    )


@transaction.atomic
def import_records(profile, records):
    new_records, _, duplicate_count = split_duplicate_records(profile, records)
    months = {
        month.month_number: month
        for month in Months.objects.all()
    }
    missing_months = sorted({
        date.fromisoformat(record['date']).month
        for record in new_records
        if date.fromisoformat(record['date']).month not in months
    })
    if missing_months:
        raise ValueError(
            'В справочнике месяцев отсутствуют номера: '
            + ', '.join(str(month) for month in missing_months)
            + '. Добавьте их и повторите импорт.'
        )
    expense_categories = {}
    income_categories = {}
    expenses = []
    incomes = []

    for record in new_records:
        transaction_date = date.fromisoformat(record['date'])
        month = months.get(transaction_date.month)
        category_name = record['category']
        if record['kind'] == 'expense':
            category = expense_categories.get(category_name)
            if category_name and category is None:
                category = _get_or_create_category(
                    CategoryExpenses, category_name
                )
                expense_categories[category_name] = category
            expenses.append(Expenses(
                month_name=month,
                category_name=category,
                cash_expenses=Decimal(record['amount']),
                date_created=transaction_date,
                waste_name=record['description'],
                outcome_currency_short_title=record['currency'],
                outcome_account_name=record['account_name'],
                payee=record['payee'],
                profile=profile,
            ))
        else:
            category = income_categories.get(category_name)
            if category_name and category is None:
                category = _get_or_create_category(
                    CategoryIncome, category_name
                )
                income_categories[category_name] = category
            incomes.append(Income(
                month_name=month,
                category_name=category,
                amount=Decimal(record['amount']),
                date_created=transaction_date,
                income_name=record['description'],
                income_currency_short_title=record['currency'],
                income_account_name=record['account_name'],
                payee=record['payee'],
                profile=profile,
            ))

    Expenses.objects.bulk_create(expenses)
    Income.objects.bulk_create(incomes)
    return len(expenses), len(incomes), duplicate_count
