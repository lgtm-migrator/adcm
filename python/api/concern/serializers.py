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

from rest_framework.relations import HyperlinkedIdentityField
from rest_framework.reverse import reverse
from rest_framework.serializers import HyperlinkedModelSerializer, SerializerMethodField

from api.utils import get_api_url_kwargs
from cm.models import ConcernItem

TYPE_VIEW_NAME_MAP = {
    "cluster": "cluster-details",
    "service": "service-details",
    "component": "servicecomponent-detail",
    "host": "host-details",
    "provider": "hostprovider-detail",
}


class ConcernItemSerializer(HyperlinkedModelSerializer):
    url = HyperlinkedIdentityField(view_name="concernitem-detail", lookup_url_kwarg="concern_pk")

    class Meta:
        model = ConcernItem
        fields = ("id", "url")


class ConcernItemUISerializer(ConcernItemSerializer):
    class Meta:
        model = ConcernItem
        fields = (*ConcernItemSerializer.Meta.fields, "type", "blocking", "reason", "cause")


class ConcernItemDetailSerializer(ConcernItemUISerializer):
    related_objects = SerializerMethodField()
    owner = SerializerMethodField()

    class Meta:
        model = ConcernItem
        fields = (*ConcernItemUISerializer.Meta.fields, "name", "related_objects", "owner")

    def get_related_objects(self, item):
        result = []
        for obj in item.related_objects:
            request = self.context.get("request", None)
            kwargs = get_api_url_kwargs(obj, request, no_obj_type=True)
            result.append(
                {
                    "type": obj.prototype.type,
                    "id": obj.pk,
                    "url": reverse(TYPE_VIEW_NAME_MAP[obj.prototype.type], kwargs=kwargs, request=request),
                }
            )
        return result

    def get_owner(self, item):
        request = self.context.get("request", None)
        kwargs = get_api_url_kwargs(item.owner, request, no_obj_type=True)
        return {
            "type": item.owner.prototype.type,
            "id": item.owner.pk,
            "url": reverse(
                f"{TYPE_VIEW_NAME_MAP[item.owner.prototype.type]}",
                kwargs=kwargs,
                request=request,
            ),
        }
