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

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED

from adcm.tests.base import BaseTestCase
from cm.models import (
    ADCM,
    Action,
    ActionType,
    Bundle,
    Cluster,
    JobLog,
    Prototype,
    TaskLog,
)
from rbac.models import Policy, Role
from rbac.upgrade.role import init_roles


class TestJobAPI(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        bundle = Bundle.objects.create()
        self.adcm_prototype = Prototype.objects.create(bundle=bundle, type="adcm")
        self.adcm = ADCM.objects.create(
            prototype=self.adcm_prototype,
            name="ADCM",
        )
        self.action = Action.objects.create(
            display_name="test_adcm_action",
            prototype=self.adcm_prototype,
            type=ActionType.Job,
            state_available="any",
        )
        self.task = TaskLog.objects.create(
            object_id=self.adcm.pk,
            object_type=ContentType.objects.get(app_label="cm", model="adcm"),
            start_date=datetime.now(tz=ZoneInfo("UTC")),
            finish_date=datetime.now(tz=ZoneInfo("UTC")),
            action=self.action,
        )
        self.job_1 = JobLog.objects.create(
            status="created",
            start_date=datetime.now(tz=ZoneInfo("UTC")),
            finish_date=datetime.now(tz=ZoneInfo("UTC")) + timedelta(days=1),
        )
        self.job_2 = JobLog.objects.create(
            status="failed",
            start_date=datetime.now(tz=ZoneInfo("UTC")) + timedelta(days=1),
            finish_date=datetime.now(tz=ZoneInfo("UTC")) + timedelta(days=2),
            action=self.action,
            task=self.task,
            pid=self.job_1.pid + 1,
        )

    def test_list(self):
        response: Response = self.client.get(path=reverse("joblog-list"))

        self.assertEqual(len(response.data["results"]), 2)

    def test_list_filter_action_id(self):
        response: Response = self.client.get(reverse("joblog-list"), {"action_id": self.action.pk})

        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.job_2.pk)

    def test_list_filter_task_id(self):
        response: Response = self.client.get(reverse("joblog-list"), {"task_id": self.task.pk})

        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.job_2.pk)

    def test_list_filter_pid(self):
        response: Response = self.client.get(reverse("joblog-list"), {"pid": self.job_1.pid})

        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["pid"], self.job_1.pid)

    def test_list_filter_status(self):
        response: Response = self.client.get(reverse("joblog-list"), {"status": self.job_1.status})

        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["status"], self.job_1.status)

    def test_list_filter_start_date(self):
        response: Response = self.client.get(
            reverse("joblog-list"),
            {"start_date": self.job_1.start_date.isoformat()},
        )

        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.job_1.pk)

    def test_list_filter_finish_date(self):
        response: Response = self.client.get(
            reverse("joblog-list"),
            {"finish_date": self.job_2.finish_date.isoformat()},
        )

        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.job_2.pk)

    def test_list_ordering_status(self):
        response: Response = self.client.get(reverse("joblog-list"), {"ordering": "status"})

        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.job_1.pk)
        self.assertEqual(response.data["results"][1]["id"], self.job_2.pk)

    def test_list_ordering_status_reverse(self):
        response: Response = self.client.get(reverse("joblog-list"), {"ordering": "-status"})

        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.job_2.pk)
        self.assertEqual(response.data["results"][1]["id"], self.job_1.pk)

    def test_list_ordering_start_date(self):
        response: Response = self.client.get(reverse("joblog-list"), {"ordering": "start_date"})

        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.job_1.pk)
        self.assertEqual(response.data["results"][1]["id"], self.job_2.pk)

    def test_list_ordering_start_date_reverse(self):
        response: Response = self.client.get(reverse("joblog-list"), {"ordering": "-start_date"})

        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.job_2.pk)
        self.assertEqual(response.data["results"][1]["id"], self.job_1.pk)

    def test_list_ordering_finish_date(self):
        response: Response = self.client.get(reverse("joblog-list"), {"ordering": "finish_date"})

        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.job_1.pk)
        self.assertEqual(response.data["results"][1]["id"], self.job_2.pk)

    def test_list_ordering_finish_date_reverse(self):
        response: Response = self.client.get(reverse("joblog-list"), {"ordering": "-finish_date"})

        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.job_2.pk)
        self.assertEqual(response.data["results"][1]["id"], self.job_1.pk)

    def test_retrieve(self):
        response: Response = self.client.get(
            reverse("joblog-detail", kwargs={"job_pk": self.job_2.pk}),
        )

        self.assertEqual(response.data["id"], self.job_2.pk)

    def test_log_files(self):
        bundle = self.upload_and_load_bundle(
            path=Path(
                settings.BASE_DIR,
                "python/api/tests/files/no-log-files.tar",
            ),
        )

        action = Action.objects.get(name="adcm_check")
        cluster_prototype = Prototype.objects.get(bundle=bundle, type="cluster")
        cluster = Cluster.objects.create(name="test_cluster", prototype=cluster_prototype)

        with patch("cm.job.run_task"):
            response: Response = self.client.post(
                path=reverse("run-task", kwargs={"cluster_id": cluster.pk, "action_id": action.pk})
            )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        job = JobLog.objects.get(action=action)

        response: Response = self.client.get(
            reverse("joblog-detail", kwargs={"job_pk": job.pk}),
        )

        self.assertEqual(len(response.data["log_files"]), 2)

    def test_task_permissions(self):
        bundle = self.upload_and_load_bundle(
            path=Path(
                settings.BASE_DIR,
                "python/api/tests/files/no-log-files.tar",
            ),
        )

        action = Action.objects.get(name="adcm_check")
        cluster_prototype = Prototype.objects.get(bundle=bundle, type="cluster")
        cluster = Cluster.objects.create(name="test_cluster", prototype=cluster_prototype)

        init_roles()
        role = Role.objects.get(name="Cluster Administrator")
        policy = Policy.objects.create(name="test_policy", role=role)
        policy.user.add(self.no_rights_user)
        policy.add_object(cluster)
        policy.apply()

        with self.no_rights_user_logged_in:
            with patch("cm.job.run_task"):
                response: Response = self.client.post(
                    path=reverse(
                        "run-task", kwargs={"cluster_id": cluster.pk, "action_id": action.pk}
                    )
                )

            response: Response = self.client.get(reverse("joblog-list"))

            self.assertIn(
                JobLog.objects.get(action=action).pk,
                {job_data["id"] for job_data in response.data["results"]},
            )

            response: Response = self.client.get(reverse("tasklog-list"))

            self.assertIn(
                TaskLog.objects.get(action=action).pk,
                {job_data["id"] for job_data in response.data["results"]},
            )
