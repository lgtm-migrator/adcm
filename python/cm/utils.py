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
from typing import Any


def dict_json_get_or_create(path: str, field: str, value: Any = None) -> Any:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if field not in data:
        data[field] = value
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    return data[field]
