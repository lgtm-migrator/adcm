# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# Generated by Django 3.1.2 on 2021-04-27 08:53
# pylint: disable=line-too-long

import django.db.models.deletion
from django.db import migrations, models


def fix_tasklog(apps, schema_editor):
    TaskLog = apps.get_model('cm', 'TaskLog')
    Action = apps.get_model('cm', 'Action')
    for task in TaskLog.objects.all():
        if task.old_action_id:
            try:
                action = Action.objects.get(id=task.old_action_id)
                task.action = action
                if task.attr is None:
                    task.attr = {}
                task.save()
            except Action.DoesNotExist:
                pass


def fix_joblog(apps, schema_editor):
    JobLog = apps.get_model('cm', 'JobLog')
    TaskLog = apps.get_model('cm', 'TaskLog')
    Action = apps.get_model('cm', 'Action')
    SubAction = apps.get_model('cm', 'SubAction')
    for job in JobLog.objects.all():
        if job.old_action_id:
            try:
                action = Action.objects.get(id=job.old_action_id)
                job.action = action
            except Action.DoesNotExist:
                pass
        if job.old_sub_action_id:
            try:
                sub_action = SubAction.objects.get(id=job.old_sub_action_id)
                job.sub_action = sub_action
            except SubAction.DoesNotExist:
                pass
        try:
            task = TaskLog.objects.get(id=job.old_task_id)
            job.task = task
        except TaskLog.DoesNotExist:
            pass
        job.save()


def fix_checklog(apps, schema_editor):
    JobLog = apps.get_model('cm', 'JobLog')
    CheckLog = apps.get_model('cm', 'CheckLog')
    for cl in CheckLog.objects.all():
        if cl.old_job_id:
            try:
                job = JobLog.objects.get(id=cl.old_job_id)
                cl.job = job
                cl.save()
            except JobLog.DoesNotExist:
                pass


def fix_grouplog(apps, schema_editor):
    JobLog = apps.get_model('cm', 'JobLog')
    GroupCheckLog = apps.get_model('cm', 'GroupCheckLog')
    for cl in GroupCheckLog.objects.all():
        if cl.old_job_id:
            try:
                job = JobLog.objects.get(id=cl.old_job_id)
                cl.job = job
                cl.save()
            except JobLog.DoesNotExist:
                pass


class Migration(migrations.Migration):

    dependencies = [
        ('cm', '0065_auto_20210220_0902'),
    ]

    operations = [
        migrations.RenameField(
            model_name='joblog',
            old_name='action_id',
            new_name='old_action_id',
        ),
        migrations.AlterField(
            model_name='joblog',
            name='old_action_id',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RenameField(
            model_name='joblog',
            old_name='sub_action_id',
            new_name='old_sub_action_id',
        ),
        migrations.RenameField(
            model_name='joblog',
            old_name='task_id',
            new_name='old_task_id',
        ),
        migrations.RenameField(
            model_name='tasklog',
            old_name='action_id',
            new_name='old_action_id',
        ),
        migrations.AlterField(
            model_name='tasklog',
            name='old_action_id',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='joblog',
            name='action',
            field=models.ForeignKey(
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='cm.action',
            ),
        ),
        migrations.AddField(
            model_name='joblog',
            name='sub_action',
            field=models.ForeignKey(
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='cm.subaction',
            ),
        ),
        migrations.AddField(
            model_name='joblog',
            name='task',
            field=models.ForeignKey(
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='cm.tasklog',
            ),
        ),
        migrations.AddField(
            model_name='tasklog',
            name='action',
            field=models.ForeignKey(
                default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='cm.action'
            ),
        ),
        migrations.RemoveConstraint(
            model_name='groupchecklog',
            name='unique_group_job',
        ),
        migrations.RenameField(
            model_name='checklog',
            old_name='job_id',
            new_name='old_job_id',
        ),
        migrations.RenameField(
            model_name='groupchecklog',
            old_name='job_id',
            new_name='old_job_id',
        ),
        migrations.AddField(
            model_name='checklog',
            name='job',
            field=models.ForeignKey(
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='cm.joblog',
            ),
        ),
        migrations.AddField(
            model_name='groupchecklog',
            name='job',
            field=models.ForeignKey(
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='cm.joblog',
            ),
        ),
        migrations.AddConstraint(
            model_name='groupchecklog',
            constraint=models.UniqueConstraint(fields=('job', 'title'), name='unique_group_job'),
        ),
        migrations.RunPython(fix_tasklog),
        migrations.RunPython(fix_joblog),
        migrations.RunPython(fix_checklog),
        migrations.RunPython(fix_grouplog),
        migrations.RemoveField(
            model_name='checklog',
            name='old_job_id',
        ),
        migrations.RemoveField(
            model_name='groupchecklog',
            name='old_job_id',
        ),
        migrations.RemoveField(
            model_name='joblog',
            name='old_action_id',
        ),
        migrations.RemoveField(
            model_name='joblog',
            name='old_sub_action_id',
        ),
        migrations.RemoveField(
            model_name='joblog',
            name='old_task_id',
        ),
        migrations.RemoveField(
            model_name='tasklog',
            name='old_action_id',
        ),
    ]
