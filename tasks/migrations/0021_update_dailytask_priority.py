# Generated manually to update DailyTask priority choices

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0020_dailytask'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dailytask',
            name='priority',
            field=models.PositiveIntegerField(
                choices=[
                    (1, 'Низкий'),
                    (2, 'Средний'),
                    (3, 'Высокий'),
                ],
                default=2,
                verbose_name='Приоритет задачи',
            ),
        ),
    ]