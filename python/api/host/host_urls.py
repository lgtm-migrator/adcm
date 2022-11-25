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


from django.urls import include, path

from api.host.urls import router as host_viewset_router
from api.host.views import StatusList

urlpatterns = [
    *host_viewset_router.urls,
    path(
        "<int:host_id>/",
        include(
            [
                path("config/", include("api.config.urls"), {"object_type": "host"}),
                path("action/", include("api.action.urls"), {"object_type": "host"}),
                path("status/", StatusList.as_view(), name="host-status"),
            ]
        ),
    ),
]
