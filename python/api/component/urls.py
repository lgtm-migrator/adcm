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
from rest_framework.routers import DefaultRouter

from api.component.views import ComponentViewSet

router = DefaultRouter()
router.register(r"", ComponentViewSet, basename="component")

urlpatterns = [
    *router.urls,
    path(
        "<int:component_pk>/config/", include("api.config.urls"), {"object_type": "component"}, name="component-config"
    ),
    path(
        "<int:component_pk>/action/", include("api.action.urls"), {"object_type": "component"}, name="component-action"
    ),
]
