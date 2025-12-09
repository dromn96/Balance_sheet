from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()

class Profile(models.Model):
    user = models.OneToOneField(User, verbose_name='ID', on_delete=models.CASCADE, null=True, blank=True)
    bank_acсount = models.IntegerField(verbose_name='Деньги на банковском счете', default=0)
    cash = models.IntegerField(verbose_name='Наличные деньги ', default=0)

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

    def __str__(self):
        if self.user:
            return self.user.username
        return self.id

class Months(models.Model):
    month_name = models.CharField(max_length=255, verbose_name='Месяц')
    month_number = models.IntegerField(verbose_name='Номер')

    class Meta:
        verbose_name = 'Месяц'
        verbose_name_plural = 'Месяцев'

    def __str__(self):
        return self.month_name

class CategoryExpenses(models.Model):
    category_name = models.CharField(max_length=255, verbose_name='Категория расходов')
    category_place_on_the_list = models.IntegerField(verbose_name='Номер в списке')
    limit = models.IntegerField(null=True, verbose_name='Лимит расходов по категории')

    class Meta:
        verbose_name = 'Категория расхода'
        verbose_name_plural = 'Категории расходов'

    def __str__(self):
        return self.category_name

class CategoryIncome(models.Model):
    category_name = models.CharField(max_length=255, verbose_name='Категория расходов')
    category_place_on_the_list = models.IntegerField(verbose_name='Номер в списке')

    class Meta:
        verbose_name = 'Категория дохода'
        verbose_name_plural = 'Категории доходов'

    def __str__(self):
        return self.category_name

class Income(models.Model):
    month_name = models.ForeignKey(Months, verbose_name='Месяц', null=True, on_delete=models.SET_NULL)
    category_name = models.ForeignKey(CategoryIncome, verbose_name='Доход', null=True, on_delete=models.SET_NULL)
    amount = models.IntegerField(null=True, verbose_name='Сумма дохода')
    date_created = models.DateField(verbose_name='Дата дохода')
    income_name = models.TextField(verbose_name='Описание дохода')
    profile = models.ForeignKey(Profile, related_name='incomes', on_delete=models.SET_NULL, null=True, blank=True)


    class Meta:
        verbose_name = 'Доход'
        verbose_name_plural = 'Доходы'

    def __str__(self):
        return str(self.income_name)

class Expenses(models.Model):
    month_name = models.ForeignKey(Months, verbose_name='Месяц', null=True, on_delete=models.SET_NULL)
    category_name = models.ForeignKey(CategoryExpenses, verbose_name='Категории', null=True, on_delete=models.SET_NULL)
    cash_expenses = models.IntegerField(verbose_name='Сумма расхода')
    date_created = models.DateField(verbose_name='Дата расхода', null=True, blank=True)
    waste_name = models.TextField(verbose_name='Описание расхода')
    profile = models.ForeignKey(Profile, related_name='expenses', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = 'Расход'
        verbose_name_plural = 'Расходы'

    def __str__(self):
        return str(self.waste_name)


class HugeExpenses(models.Model):
    text = models.TextField(verbose_name='Крупные траты за год')
    month_name = models.ForeignKey(Months, verbose_name='Месяц', null=True, on_delete=models.SET_NULL)
    category_name = models.ForeignKey(CategoryExpenses, verbose_name='Категории', null=True, on_delete=models.SET_NULL)
    cash_expenses = models.IntegerField(verbose_name='Расходы за наличные')

    class Meta:
        verbose_name = 'Крупные траты за год'
        verbose_name_plural = 'Крупные траты за год'

    def __str__(self):
        return str(self.month_name)

class HugeExpensesSettings(models.Model):
    category = models.ForeignKey(CategoryExpenses, verbose_name='Категория', null=True, on_delete=models.SET_NULL)
    amount = models.IntegerField(verbose_name='сумма при которой расход выводится в разделе "Крупные траты"')

    class Meta:
        verbose_name = 'Настройка для крупной траты'
        verbose_name_plural = 'Настройки для крупных трат'

    def __str__(self):
        return str(self.category)


# class User(models.Model):
#     username = models.TextField(verbose_name='Имя пользователя')
#     password = models.CharField(max_length=255, verbose_name='Пароль')
#     email = models.CharField(max_length=255, verbose_name='Электронная почта')

#     class Meta:
#         verbose_name = 'Пользователь'
#         verbose_name_plural = 'Пользователи'

#     def __str__(self):
#         return str(self.username)


