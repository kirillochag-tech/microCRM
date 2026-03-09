# Generated manually to add geolocation fields to PhotoReportItem model
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0017_task_stand_count'),
    ]

    operations = [
        migrations.AddField(
            model_name='photoreportitem',
            name='latitude',
            field=models.FloatField(
                blank=True,
                help_text='Географическая широта места съемки фото',
                null=True,
                verbose_name='Широта'
            ),
        ),
        migrations.AddField(
            model_name='photoreportitem',
            name='location_address',
            field=models.CharField(
                blank=True,
                help_text='Адрес, полученный по координатам (обратное геокодирование)',
                max_length=500,
                null=True,
                verbose_name='Адрес местоположения'
            ),
        ),
        migrations.AddField(
            model_name='photoreportitem',
            name='longitude',
            field=models.FloatField(
                blank=True,
                help_text='Географическая долгота места съемки фото',
                null=True,
                verbose_name='Долгота'
            ),
        ),
    ]