# Generated manually to add client_group and employee_group to Task
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0003_client_trading_point_address_and_more"),
        ("tasks", "0012_task_groups"),
        ("users", "0003_employeegroup_remove_customuser_employee_group_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="task",
            name="client_group",
            field=models.ForeignKey(
                blank=True,
                help_text="Группа клиентов для назначения задачи",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="clients.clientgroup",
                verbose_name="Группа клиентов",
            ),
        ),
        migrations.AlterField(
            model_name="task",
            name="employee_group",
            field=models.ForeignKey(
                blank=True,
                help_text="Группа сотрудников для назначения задачи",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="users.employeegroup",
                verbose_name="Группа сотрудников",
            ),
        ),
    ]