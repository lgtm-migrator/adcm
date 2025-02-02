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

# Generated by Django 2.0.5 on 2018-12-12 12:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cm', '0009_auto_20181113_1112'),
    ]

    operations = [
        migrations.AddField(
            model_name='cluster',
            name='issue',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='clusterobject',
            name='issue',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='host',
            name='issue',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='hostprovider',
            name='issue',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='prototype',
            name='required',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='stageprototype',
            name='required',
            field=models.BooleanField(default=False),
        ),
    ]
