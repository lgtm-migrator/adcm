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
# Generated by Django 3.0.3 on 2020-02-28 10:32
# pylint: disable=line-too-long

import json
import os

import django.db.models.deletion
from django.db import migrations, models

from adcm.settings import ENCODING_UTF_8, LOG_DIR


def get_body(job, name, type_log, format_log):
    file_path = LOG_DIR / f"{job.id}-{name}-{type_log}.{format_log}"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding=ENCODING_UTF_8) as f:
            body = f.read()
        return body
    else:
        return None


def add_logs(apps, schema_editor):
    LogStorage = apps.get_model("cm", "LogStorage")
    JobLog = apps.get_model("cm", "JobLog")

    jobs = JobLog.objects.all()
    for job in jobs:
        LogStorage.objects.create(
            job=job,
            name="ansible",
            type="stdout",
            format="txt",
            body=get_body(job, "ansible", "out", "txt"),
        )
        LogStorage.objects.create(
            job=job,
            name="ansible",
            type="stderr",
            format="txt",
            body=get_body(job, "ansible", "err", "txt"),
        )
        try:
            log_files = job.log_files
            if "check" in log_files:
                LogStorage.objects.create(
                    job=job,
                    name="ansible",
                    type="check",
                    format="json",
                    body=get_body(job, "check", "out", "json"),
                )
        except json.JSONDecodeError:
            pass


def remove_logs(apps, schema_editor):
    LogStorage = apps.get_model("cm", "LogStorage")
    JobLog = apps.get_model("cm", "JobLog")

    jobs = JobLog.objects.all()
    for job in jobs:
        LogStorage.objects.filter(job=job).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("cm", "0047_auto_20200210_1152"),
    ]

    operations = [
        migrations.AlterField(
            model_name="action",
            name="allow_to_terminate",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="stageaction",
            name="allow_to_terminate",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="LogStorage",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("name", models.TextField(default="")),
                ("body", models.TextField(blank=True, null=True)),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("stdout", "stdout"),
                            ("stderr", "stderr"),
                            ("check", "check"),
                            ("custom", "custom"),
                        ],
                        max_length=16,
                    ),
                ),
                (
                    "format",
                    models.CharField(choices=[("txt", "txt"), ("json", "json")], max_length=16),
                ),
                (
                    "job",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="cm.JobLog"),
                ),
            ],
        ),
        migrations.RunPython(add_logs, remove_logs),
    ]
