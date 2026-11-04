from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_expenses_outcome_account_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='income',
            name='income_account_name',
            field=models.CharField(blank=True, max_length=255, verbose_name='Счёт дохода'),
        ),
    ]
