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

import json
import os

from rest_framework.reverse import reverse
from rest_framework.serializers import (
    BooleanField,
    CharField,
    DateTimeField,
    HyperlinkedIdentityField,
    HyperlinkedModelSerializer,
    IntegerField,
    JSONField,
    SerializerMethodField,
)

from adcm.serializers import EmptySerializer
from api.concern.serializers import ConcernItemSerializer
from api.utils import hlink
from cm.ansible_plugin import get_check_log
from cm.config import RUN_DIR, Job
from cm.errors import AdcmEx
from cm.job import start_task
from cm.models import JobLog, TaskLog


class DataField(CharField):
    def to_representation(self, value):
        return value


class JobAction(EmptySerializer):
    name = CharField(read_only=True)
    display_name = CharField(read_only=True)
    prototype_id = IntegerField(read_only=True)
    prototype_name = CharField(read_only=True)
    prototype_type = CharField(read_only=True)
    prototype_version = CharField(read_only=True)


class JobShort(EmptySerializer):
    id = IntegerField(read_only=True)
    name = CharField(read_only=True)
    display_name = SerializerMethodField()
    status = CharField(read_only=True)
    start_date = DateTimeField(read_only=True)
    finish_date = DateTimeField(read_only=True)
    url = hlink("job-details", "id", "job_id")

    @staticmethod
    def get_display_name(obj: JobLog) -> str | None:
        if obj.sub_action:
            return obj.sub_action.display_name
        elif obj.action:
            return obj.action.display_name
        else:
            return None


class TaskListSerializer(EmptySerializer):
    id = IntegerField(read_only=True)
    pid = IntegerField(read_only=True)
    object_id = IntegerField(read_only=True)
    action_id = IntegerField(read_only=True)
    status = CharField(read_only=True)
    start_date = DateTimeField(read_only=True)
    finish_date = DateTimeField(read_only=True)
    url = hlink("task-details", "id", "task_id")


class TaskSerializer(TaskListSerializer):
    selector = JSONField(read_only=True)
    config = JSONField(required=False)
    attr = JSONField(required=False)
    hc = JSONField(required=False)
    hosts = JSONField(required=False)
    verbose = BooleanField(required=False)
    action_url = SerializerMethodField()
    action = SerializerMethodField()
    objects = SerializerMethodField()
    jobs = SerializerMethodField()
    restart = hlink("task-restart", "id", "task_id")
    terminatable = SerializerMethodField()
    cancel = hlink("task-cancel", "id", "task_id")
    download = hlink("task-download", "id", "task_id")
    object_type = SerializerMethodField()
    lock = ConcernItemSerializer(read_only=True)

    @staticmethod
    def get_terminatable(obj: TaskLog):
        if obj.action:
            allow_to_terminate = obj.action.allow_to_terminate
        else:
            allow_to_terminate = False

        if allow_to_terminate and obj.status in [Job.CREATED, Job.RUNNING]:
            return True

        return False

    def get_jobs(self, obj: TaskLog):
        return JobShort(obj.joblog_set, many=True, context=self.context).data

    def get_action(self, obj: TaskLog):
        return JobAction(obj.action, context=self.context).data

    @staticmethod
    def get_objects(obj: TaskLog) -> list:
        objects = [{"type": k, **v} for k, v in obj.selector.items()]

        return objects

    @staticmethod
    def get_object_type(obj: TaskLog):
        if obj.action:
            return obj.action.prototype.type

        return None

    def get_action_url(self, obj: TaskLog) -> str | None:
        if not obj.action_id:
            return None

        return reverse(
            "action-details", kwargs={"action_id": obj.action_id}, request=self.context["request"]
        )


class RunTaskSerializer(TaskSerializer):
    def create(self, validated_data):
        obj = start_task(
            validated_data.get("action"),
            validated_data.get("task_object"),
            validated_data.get("config", {}),
            validated_data.get("attr", {}),
            validated_data.get("hc", []),
            validated_data.get("hosts", []),
            validated_data.get("verbose", False),
        )
        obj.jobs = JobLog.objects.filter(task_id=obj.id)

        return obj


class JobSerializer(HyperlinkedModelSerializer):
    url = HyperlinkedIdentityField(view_name="job-detail", lookup_url_kwarg="job_pk")

    class Meta:
        model = JobLog
        fields = (
            "id",
            "pid",
            "task_id",
            "action_id",
            "sub_action_id",
            "status",
            "start_date",
            "finish_date",
            "url",
        )
        extra_kwargs = {"url": {"lookup_url_kwarg": "job_pk"}}


class JobRetrieveSerializer(HyperlinkedModelSerializer):
    url = HyperlinkedIdentityField(view_name="job-detail", lookup_url_kwarg="job_pk")
    action = SerializerMethodField()
    display_name = SerializerMethodField()
    objects = SerializerMethodField()
    selector = JSONField(read_only=True)
    log_dir = CharField(read_only=True)
    log_files = DataField(read_only=True)
    action_url = SerializerMethodField()
    task_url = HyperlinkedIdentityField(
        view_name="task-details",
        lookup_url_kwarg="task_id",
    )

    class Meta:
        model = JobLog
        fields = JobSerializer.Meta.fields + (
            "action",
            "display_name",
            "objects",
            "selector",
            "log_dir",
            "log_files",
            "action_url",
            "task_url",
        )
        extra_kwargs = {"url": {"lookup_url_kwarg": "job_pk"}}

    def get_action(self, obj):
        return JobAction(obj.action, context=self.context).data

    @staticmethod
    def get_objects(obj: JobLog) -> list | None:
        objects = [{"type": k, **v} for k, v in obj.task.selector.items()]

        return objects

    @staticmethod
    def get_display_name(obj: JobLog) -> str | None:
        if obj.sub_action:
            return obj.sub_action.display_name
        elif obj.action:
            return obj.action.display_name
        else:
            return None

    def get_action_url(self, obj: TaskLog) -> str | None:
        if not obj.action_id:
            return None

        return reverse(
            "action-details", kwargs={"action_id": obj.action_id}, request=self.context["request"]
        )


class LogStorageSerializer(EmptySerializer):
    id = IntegerField(read_only=True)
    name = CharField(read_only=True)
    type = CharField(read_only=True)
    format = CharField(read_only=True)
    content = SerializerMethodField()

    @staticmethod
    def _get_ansible_content(obj):
        path_file = os.path.join(RUN_DIR, f"{obj.job.id}", f"{obj.name}-{obj.type}.{obj.format}")
        try:
            with open(path_file, "r", encoding="utf_8") as f:
                content = f.read()
        except FileNotFoundError as e:
            msg = f'File "{obj.name}-{obj.type}.{obj.format}" not found'

            raise AdcmEx("LOG_NOT_FOUND", msg) from e
        return content

    def get_content(self, obj):
        content = obj.body

        if obj.type in ["stdout", "stderr"]:
            if content is None:
                content = self._get_ansible_content(obj)
        elif obj.type == "check":
            if content is None:
                content = get_check_log(obj.job_id)
            if isinstance(content, str):
                content = json.loads(content)
        elif obj.type == "custom":
            if obj.format == "json" and isinstance(content, str):
                try:
                    custom_content = json.loads(content)
                    custom_content = json.dumps(custom_content, indent=4)
                    content = custom_content
                except json.JSONDecodeError:
                    pass

        return content


class LogStorageListSerializer(LogStorageSerializer):
    url = SerializerMethodField()

    def get_url(self, obj):
        return reverse(
            "log-storage",
            kwargs={"job_id": obj.job_id, "log_id": obj.id},
            request=self.context["request"],
        )


class LogSerializer(EmptySerializer):
    tag = SerializerMethodField()
    level = SerializerMethodField()
    type = SerializerMethodField()
    content = SerializerMethodField()

    @staticmethod
    def get_tag(obj):
        if obj.type == "check":
            return obj.type

        return obj.name

    @staticmethod
    def get_level(obj):
        if obj.type == "check":
            return "out"

        return obj.type[3:]

    @staticmethod
    def get_type(obj):
        return obj.format

    @staticmethod
    def get_content(obj):
        content = obj.body

        if obj.type in ["stdout", "stderr"]:
            if content is None:
                path_file = os.path.join(
                    RUN_DIR, f"{obj.job.id}", f"{obj.name}-{obj.type}.{obj.format}"
                )
                with open(path_file, "r", encoding="utf_8") as f:
                    content = f.read()
        elif obj.type == "check":
            if content is None:
                content = get_check_log(obj.job_id)

            if isinstance(content, str):
                content = json.loads(content)

        return content
