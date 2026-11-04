from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_expenses_profile_income_profile'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expenses',
            name='cash_expenses',
            field=models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Сумма расхода'),
        ),
        migrations.AlterField(
            model_name='expenses',
            name='waste_name',
            field=models.TextField(blank=True, verbose_name='Описание расхода'),
        ),
        migrations.AddField(
            model_name='expenses',
            name='outcome_currency_short_title',
            field=models.CharField(blank=True, max_length=3, verbose_name='Валюта расхода'),
        ),
        migrations.AddField(
            model_name='expenses',
            name='payee',
            field=models.CharField(blank=True, max_length=255, verbose_name='Получатель'),
        ),
        migrations.AlterField(
            model_name='income',
            name='amount',
            field=models.DecimalField(decimal_places=2, max_digits=12, null=True, verbose_name='Сумма дохода'),
        ),
        migrations.AlterField(
            model_name='income',
            name='income_name',
            field=models.TextField(blank=True, verbose_name='Описание дохода'),
        ),
        migrations.AddField(
            model_name='income',
            name='income_currency_short_title',
            field=models.CharField(blank=True, max_length=3, verbose_name='Валюта дохода'),
        ),
        migrations.AddField(
            model_name='income',
            name='payee',
            field=models.CharField(blank=True, max_length=255, verbose_name='Получатель'),
        ),
    ]
