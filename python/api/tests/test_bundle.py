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

from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED

from adcm.tests.base import BaseTestCase
from cm.bundle import get_hash


class TestBundle(BaseTestCase):
    def tearDown(self) -> None:
        Path(settings.DOWNLOAD_DIR, self.test_bundle_filename).unlink(missing_ok=True)

    def upload_bundle(self):
        with open(self.test_bundle_path, encoding="utf-8") as f:
            return self.client.post(
                path=reverse("upload-bundle"),
                data={"file": f},
            )

    def test_upload_bundle(self) -> None:
        response: Response = self.upload_bundle()

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertTrue(Path(settings.DOWNLOAD_DIR, self.test_bundle_filename).exists())

    def test_load_bundle(self):
        self.upload_bundle()

        response: Response = self.client.post(
            path=reverse("load-bundle"),
            data={"bundle_file": self.test_bundle_filename},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["hash"], get_hash(self.test_bundle_path))

    def test_load_servicemap(self):
        with patch("api.stack.views.load_service_map"):
            response: Response = self.client.put(
                path=reverse("load-servicemap"),
            )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_load_hostmap(self):
        with patch("api.stack.views.load_host_map"):
            response: Response = self.client.put(
                path=reverse("load-hostmap"),
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
