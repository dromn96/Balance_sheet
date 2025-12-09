from collections import OrderedDict
from django.db.models import Sum

from core.models import Expenses, CategoryExpenses


def get_expenses_by_category(profile, year=2025):

    expenses_by_category = Expenses.objects.filter(date_created__year=year, profile=profile) \
        .values('category_name__category_name', 'month_name__month_number') \
        .annotate(total_amount=Sum('cash_expenses'))
    category_list = CategoryExpenses.objects.all()
    print(expenses_by_category)

    data_by_category = {}

    for item in expenses_by_category:
        category_name = item['category_name__category_name']
        month = item['month_name__month_number']
        amount = item['total_amount']

        if category_name not in data_by_category:
            data_by_category[category_name] = {
                'months': {str(month): amount}, 'total': 0}
        else:
            data_by_category[category_name]['months'].update(
                {str(month): amount})

        data_by_category[category_name]['total'] += amount

    for category_name, data in data_by_category.items():
        data['average'] = data['total'] / len(data['months'])

    category_list_order = category_list.order_by(
            'category_place_on_the_list')

    data_by_category_ordered = OrderedDict()
    total_sums_by_category = {}

    for category in category_list_order:
        category_name = category.category_name

        if category_name not in data_by_category:
            continue

        data_by_category_ordered[category_name] = data_by_category[category_name]

        print(data_by_category_ordered)

    return data_by_category_ordered


