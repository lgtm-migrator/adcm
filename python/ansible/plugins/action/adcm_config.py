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

# pylint: disable=wrong-import-position, import-error

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys

sys.path.append('/adcm/python')
import adcm.init_django  # pylint: disable=unused-import
from cm.ansible_plugin import (
    ContextActionModule,
    set_cluster_config,
    set_component_config,
    set_component_config_by_name,
    set_host_config,
    set_provider_config,
    set_service_config,
    set_service_config_by_name,
)

ANSIBLE_METADATA = {'metadata_version': '1.1', 'supported_by': 'Arenadata'}
DOCUMENTATION = r'''
---
module: adcm_config
short_description: Change values in config in runtime
description:
  - This is special ADCM only module which is useful for setting of specified config key for various ADCM objects.
  - There is support of cluster, service, host and providers config.
  - This one is allowed to be used in various execution contexts.
options:
  - option-name: type
    required: true
    choises:
      - cluster
      - service
      - host
      - provider
    description: type of object which should be changed

  - option-name: key
    required: true
    type: string
    description: name of key which should be set

  - option-name: value
    required: true
    description: value which should be set

  - option-name: service_name
    required: false
    type: string
    description: useful in cluster context only. In that context you are able to set a config value for a service belongs to the cluster.

notes:
  - If type is 'service', there is no needs to specify service_name
'''
EXAMPLES = r'''
- adcm_config:
    type: "service"
    service_name: "First"
    key: "some_int"
    value: *new_int
  register: out

- adcm_config:
    type: "cluster"
    key: "some_map"
    value:
      key1: value1
      key2: value2
'''
RETURN = r'''
value:
  returned: success
  type: complex
'''


class ActionModule(ContextActionModule):

    _VALID_ARGS = frozenset(('type', 'key', 'value', 'service_name', 'component_name', 'host_id'))
    _MANDATORY_ARGS = ('type', 'key', 'value')

    def _do_cluster(self, task_vars, context):
        res = self._wrap_call(
            set_cluster_config,
            context['cluster_id'],
            self._task.args["key"],
            self._task.args["value"],
        )
        res['value'] = self._task.args["value"]
        return res

    def _do_service_by_name(self, task_vars, context):
        res = self._wrap_call(
            set_service_config_by_name,
            context['cluster_id'],
            self._task.args["service_name"],
            self._task.args["key"],
            self._task.args["value"],
        )
        res['value'] = self._task.args["value"]
        return res

    def _do_service(self, task_vars, context):
        res = self._wrap_call(
            set_service_config,
            context['cluster_id'],
            context['service_id'],
            self._task.args["key"],
            self._task.args["value"],
        )
        res['value'] = self._task.args["value"]
        return res

    def _do_host(self, task_vars, context):
        res = self._wrap_call(set_host_config, context['host_id'], self._task.args["key"], self._task.args["value"])
        res['value'] = self._task.args["value"]
        return res

    def _do_host_from_provider(self, task_vars, context):
        # TODO: Check that host is in provider
        res = self._wrap_call(
            set_host_config,
            self._task.args['host_id'],
            self._task.args["key"],
            self._task.args["value"],
        )
        res['value'] = self._task.args["value"]
        return res

    def _do_provider(self, task_vars, context):
        res = self._wrap_call(
            set_provider_config,
            context['provider_id'],
            self._task.args["key"],
            self._task.args["value"],
        )
        res['value'] = self._task.args["value"]
        return res

    def _do_component_by_name(self, task_vars, context):
        res = self._wrap_call(
            set_component_config_by_name,
            context['cluster_id'],
            context['service_id'],
            self._task.args['component_name'],
            self._task.args.get('service_name', None),
            self._task.args['key'],
            self._task.args['value'],
        )
        res['value'] = self._task.args['value']
        return res

    def _do_component(self, task_vars, context):
        res = self._wrap_call(
            set_component_config,
            context['component_id'],
            self._task.args['key'],
            self._task.args['value'],
        )
        res['value'] = self._task.args['value']
        return res
