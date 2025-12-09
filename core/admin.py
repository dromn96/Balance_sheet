from django.contrib import admin
from .models import *
from import_export import resources
from import_export .admin import ImportExportModelAdmin

admin.site.register(Months)
admin.site.register(CategoryExpenses)
admin.site.register(CategoryIncome)
admin.site.register(Income)
admin.site.register(Expenses)
admin.site.register(HugeExpenses)
admin.site.register(Profile)
admin.site.register(HugeExpensesSettings)

# class ExpensesEdit(resources.ModelResource):
#     class Meta:
#         model = Expenses
#
# @admin.register(Expenses)
# class BalanceAdmin(ImportExportModelAdmin):
#     resource_class = [ExpensesEdit]

