from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_transaction_import_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='expenses',
            name='outcome_account_name',
            field=models.CharField(blank=True, max_length=255, verbose_name='Счёт расхода'),
        ),
    ]
