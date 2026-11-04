from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

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
