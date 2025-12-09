from django.urls import path
from .views import *

urlpatterns = [
    path('', main),
    path('incomes', incomes),
    path('incomes/add', add_incomes),
    path('incomes/category', incomes_category),
    path('incomes/category/add', add_income_category),
    path('incomes/export', export_incomes_to_excel),
    path('incomes/<int:income_id>/edit', edit_income),
    path('incomes/<int:income_id>/delete', delete_income),
    path('expenses', expenses),
    path('expenses/add', add_expenses),
    path('expenses/category', expenses_category),
    path('expenses/export', export_expenses_to_excel),
    path('expenses/category/add', add_expenses_category),
    path('expenses/<int:expense_id>/edit', edit_expense),
    path('expenses/<int:expense_id>/delete', delete_expense),
    path('huge_expenses', huge_expenses),
    # path('huge_expenses/add', add_huge_expenses),

    # path('expenses/category/delete', delete_expenses_category)
]