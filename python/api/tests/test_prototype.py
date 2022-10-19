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

from django.urls import reverse
from rest_framework.response import Response

from adcm.tests.base import BaseTestCase
from cm.models import Bundle, Prototype


class TestPrototypeAPI(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.bundle_1 = Bundle.objects.create(name="test_bundle_1")
        self.bundle_2 = Bundle.objects.create(name="test_bundle_2")
        self.prototype_1 = Prototype.objects.create(
            bundle=self.bundle_1,
            type="adcm",
            name="test_prototype_1",
            display_name="test_prototype_1",
            version_order=1,
        )
        self.prototype_2 = Prototype.objects.create(
            bundle=self.bundle_2,
            type="cluster",
            name="test_prototype_2",
            display_name="test_prototype_2",
            version_order=2,
        )

    def test_list(self):
        response: Response = self.client.get(path=reverse("prototype-list"))

        self.assertEqual(len(response.data["results"]), 2)

    def test_list_filter_name(self):
        response: Response = self.client.get(
            reverse("prototype-list"), {"name": "test_prototype_2"}
        )

        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.prototype_2.pk)

    def test_list_filter_bundle_id(self):
        response: Response = self.client.get(
            reverse("prototype-list"),
            {"bundle_id": self.bundle_1.pk},
        )

        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.prototype_1.pk)

    def test_list_ordering_display_name(self):
        response: Response = self.client.get(
            reverse("prototype-list"), {"ordering": "display_name"}
        )

        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.prototype_1.pk)
        self.assertEqual(response.data["results"][1]["id"], self.prototype_2.pk)

    def test_list_ordering_display_name_reverse(self):
        response: Response = self.client.get(
            reverse("prototype-list"), {"ordering": "-display_name"}
        )

        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.prototype_2.pk)
        self.assertEqual(response.data["results"][1]["id"], self.prototype_1.pk)

    def test_list_ordering_version_order(self):
        response: Response = self.client.get(
            reverse("prototype-list"), {"ordering": "version_order"}
        )

        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.prototype_1.pk)
        self.assertEqual(response.data["results"][1]["id"], self.prototype_2.pk)

    def test_list_ordering_version_order_reverse(self):
        response: Response = self.client.get(
            reverse("prototype-list"), {"ordering": "-version_order"}
        )

        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.prototype_2.pk)
        self.assertEqual(response.data["results"][1]["id"], self.prototype_1.pk)

    def test_retrieve(self):
        response: Response = self.client.get(
            reverse("prototype-detail", kwargs={"prototype_pk": self.prototype_2.pk}),
        )

        self.assertEqual(response.data["id"], self.prototype_2.pk)
