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

import json
import os
import sys

from django.conf import settings

# later
PYTHON_DIR = sys.exec_prefix
PYTHON_EXECUTABLE = sys.executable
PYTHON_VERSION = f'{sys.version_info.major}.{sys.version_info.minor}'
PYTHON_SITE_PACKAGES = os.path.join(PYTHON_DIR, f'lib/python{PYTHON_VERSION}/site-packages')
# ---


class Job:
    CREATED = 'created'
    SUCCESS = 'success'
    FAILED = 'failed'
    RUNNING = 'running'
    LOCKED = 'locked'
    ABORTED = 'aborted'
