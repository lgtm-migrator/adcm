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


from django_filters.rest_framework import BaseInFilter, CharFilter, FilterSet

from cm.models import Prototype


class StringInFilter(BaseInFilter, CharFilter):
    pass


class PrototypeListFilter(FilterSet):
    name = StringInFilter(label="name", field_name="name", lookup_expr="in")
    parent_name = StringInFilter(label="parent_name", field_name="parent", lookup_expr="name__in")

    class Meta:
        model = Prototype
        fields = ["bundle_id", "type"]
