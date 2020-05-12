#!/usr/bin/python
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

# pylint: disable=wrong-import-position, unused-import, import-error

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1', 'supported_by': 'Arenadata'}

DOCUMENTATION = r'''
---
module: adcm_delete_host
short_description: delete host from ADCM DB
description:
    - The C(adcm_delete_host) module is intended to delete host from ADCM DB.
      This module should be run in host context. Host Id is taken from context.
options:
'''

EXAMPLES = r'''
 - name: delete current host
   adcm_delete_host:
'''

RETURN = r'''
'''

import sys
from ansible.errors import AnsibleError
from ansible.plugins.action import ActionBase

sys.path.append('/adcm/python')
import adcm.init_django
import cm.api
from cm.ansible_plugin import get_context_id
from cm.errors import AdcmEx
from cm.logger import log


class ActionModule(ActionBase):

    TRANSFERS_FILES = False
    _VALID_ARGS = frozenset(())

    def run(self, tmp=None, task_vars=None):
        super(ActionModule, self).run(tmp, task_vars)
        msg = 'You can delete host only in host context'
        host_id = get_context_id(task_vars, 'host', 'host_id', msg)
        log.info('ansible module adcm_delete_host: host #%s', host_id)

        try:
            cm.api.delete_host_by_id(host_id)
        except AdcmEx as e:
            raise AnsibleError(e.code + ":" + e.msg)

        return {"failed": False, "changed": True}
