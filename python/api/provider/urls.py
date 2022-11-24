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

from api.provider.views import ProviderUpgradeViewSet, ProviderViewSet

router = DefaultRouter()
router.register("", ProviderViewSet)
router.register("", ProviderUpgradeViewSet, basename="hostprovider-upgrade")

urlpatterns = [
    *router.urls,
    path("<int:provider_pk>/config/", include("api.config.urls"), {"object_type": "provider"}, name="provider-config"),
    path("<int:provider_pk>/action/", include("api.action.urls"), {"object_type": "provider"}, name="provider-action"),
    path("<int:provider_pk>/host/", include("api.host.provider_urls")),
    path(
        "<int:provider_pk>/upgrade/", ProviderUpgradeViewSet.as_view({"get": "list"}), name="hostprovider-upgrade-list"
    ),
    path(
        "<int:provider_pk>/upgrade/<int:upgrade_pk>/",
        ProviderUpgradeViewSet.as_view({"get": "retrieve"}),
        name="hostprovider-upgrade-detail",
    ),
    path(
        "<int:provider_pk>/upgrade/<int:upgrade_pk>/do/",
        ProviderUpgradeViewSet.as_view({"post": "do"}),
        name="do-provider-upgrade",
    ),
]
# fmt: on
