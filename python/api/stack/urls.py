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

from api.stack.root import StackRoot
from api.stack.views import (
    AdcmTypeDetail,
    AdcmTypeList,
    BundleViewSet,
    ClusterTypeDetail,
    ClusterTypeList,
    ComponentList,
    ComponentTypeDetail,
    HostTypeDetail,
    HostTypeList,
    LoadBundleView,
    ProtoActionDetail,
    PrototypeDetail,
    PrototypeList,
    ProviderTypeDetail,
    ProviderTypeList,
    ServiceDetail,
    ServiceList,
    ServiceProtoActionList,
    UploadBundleView,
    load_hostmap_view,
    load_servicemap_view,
)

PROTOTYPE_ID = "<int:prototype_id>/"

router = DefaultRouter()
router.register("bundle", BundleViewSet)


urlpatterns = [
    *router.urls,
    path("", StackRoot.as_view(), name="stack"),
    path("upload/", UploadBundleView.as_view(), name="upload-bundle"),
    path("load/", LoadBundleView.as_view(), name="load-bundle"),
    path("load/servicemap/", load_servicemap_view, name="load-servicemap"),
    path("load/hostmap/", load_hostmap_view, name="load-hostmap"),
    path(
        "bundle/<int:bundle_pk>/update/",
        BundleViewSet.as_view({"put": "update_bundle"}),
        name="bundle-update",
    ),
    path(
        "bundle/<int:bundle_pk>/license/accept/",
        BundleViewSet.as_view({"put": "accept_license"}),
        name="accept-license",
    ),
    path("action/<int:action_id>/", ProtoActionDetail.as_view(), name="action-details"),
    path(
        "prototype/",
        include(
            [
                path("", PrototypeList.as_view(), name="prototype"),
                path(PROTOTYPE_ID, PrototypeDetail.as_view(), name="prototype-details"),
            ]
        ),
    ),
    path(
        "service/",
        include(
            [
                path("", ServiceList.as_view(), name="service-type"),
                path(
                    PROTOTYPE_ID,
                    include(
                        [
                            path("", ServiceDetail.as_view(), name="service-type-details"),
                            path(
                                "action/", ServiceProtoActionList.as_view(), name="service-actions"
                            ),
                        ]
                    ),
                ),
            ]
        ),
    ),
    path(
        "component/",
        include(
            [
                path("", ComponentList.as_view(), name="component-type"),
                path(PROTOTYPE_ID, ComponentTypeDetail.as_view(), name="component-type-details"),
            ]
        ),
    ),
    path(
        "provider/",
        include(
            [
                path("", ProviderTypeList.as_view(), name="provider-type"),
                path(PROTOTYPE_ID, ProviderTypeDetail.as_view(), name="provider-type-details"),
            ]
        ),
    ),
    path(
        "host/",
        include(
            [
                path("", HostTypeList.as_view(), name="host-type"),
                path(PROTOTYPE_ID, HostTypeDetail.as_view(), name="host-type-details"),
            ]
        ),
    ),
    path(
        "cluster/",
        include(
            [
                path("", ClusterTypeList.as_view(), name="cluster-type"),
                path(PROTOTYPE_ID, ClusterTypeDetail.as_view(), name="cluster-type-details"),
            ]
        ),
    ),
    path(
        "adcm/",
        include(
            [
                path("", AdcmTypeList.as_view(), name="adcm-type"),
                path(PROTOTYPE_ID, AdcmTypeDetail.as_view(), name="adcm-type-details"),
            ]
        ),
    ),
]
