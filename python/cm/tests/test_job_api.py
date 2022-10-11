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
from zoneinfo import ZoneInfo

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rest_framework.response import Response

from adcm.tests.base import BaseTestCase
from cm.models import ADCM, Action, ActionType, Bundle, JobLog, Prototype, TaskLog


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
            start_date=datetime.now(),
            finish_date=datetime.now(),
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
        response: Response = self.client.get(path=reverse("job-list"))

        self.assertEqual(len(response.data["results"]), 2)

    def test_list_filter_action_id(self):
        response: Response = self.client.get(reverse("job-list"), {"action_id": self.action.pk})

        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.job_2.pk)

    def test_list_filter_task_id(self):
        response: Response = self.client.get(reverse("job-list"), {"task_id": self.task.pk})

        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.job_2.pk)

    def test_list_filter_pid(self):
        response: Response = self.client.get(reverse("job-list"), {"pid": self.job_1.pid})

        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["pid"], self.job_1.pid)

    def test_list_filter_start_date(self):
        response: Response = self.client.get(
            reverse("job-list"),
            {"start_date": self.job_1.start_date.isoformat()},
        )

        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.job_1.pk)

    def test_list_filter_finish_date(self):
        response: Response = self.client.get(
            reverse("job-list"),
            {"finish_date": self.job_2.finish_date.isoformat()},
        )

        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.job_2.pk)

    def test_list_ordering_status(self):
        response: Response = self.client.get(reverse("job-list"), {"ordering": "status"})

        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.job_1.pk)
        self.assertEqual(response.data["results"][1]["id"], self.job_2.pk)

    def test_list_ordering_status_reverse(self):
        response: Response = self.client.get(reverse("job-list"), {"ordering": "-status"})

        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.job_2.pk)
        self.assertEqual(response.data["results"][1]["id"], self.job_1.pk)

    def test_list_ordering_start_date(self):
        response: Response = self.client.get(reverse("job-list"), {"ordering": "start_date"})

        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.job_1.pk)
        self.assertEqual(response.data["results"][1]["id"], self.job_2.pk)

    def test_list_ordering_start_date_reverse(self):
        response: Response = self.client.get(reverse("job-list"), {"ordering": "-start_date"})

        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.job_2.pk)
        self.assertEqual(response.data["results"][1]["id"], self.job_1.pk)

    def test_list_ordering_finish_date(self):
        response: Response = self.client.get(reverse("job-list"), {"ordering": "finish_date"})

        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.job_1.pk)
        self.assertEqual(response.data["results"][1]["id"], self.job_2.pk)

    def test_list_ordering_finish_date_reverse(self):
        response: Response = self.client.get(reverse("job-list"), {"ordering": "-finish_date"})

        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.job_2.pk)
        self.assertEqual(response.data["results"][1]["id"], self.job_1.pk)

    def test_retrieve(self):
        response: Response = self.client.get(
            reverse("job-detail", kwargs={"job_pk": self.job_2.pk}),
        )

        self.assertEqual(response.data["id"], self.job_2.pk)
