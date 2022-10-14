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

import sys
import os
import argparse
from pathlib import Path
from typing import TextIO

APACHE_LICENCE_PY = [
    '# Licensed under the Apache License, Version 2.0 (the "License");\n',
    '# you may not use this file except in compliance with the License.\n',
    '# You may obtain a copy of the License at\n',
    '#\n',
    '#      http://www.apache.org/licenses/LICENSE-2.0\n',
    '#\n',
    '# Unless required by applicable law or agreed to in writing, software\n',
    '# distributed under the License is distributed on an "AS IS" BASIS,\n',
    '# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.\n',
    '# See the License for the specific language governing permissions and\n',
    '# limitations under the License.\n',
    '\n'
]

APACHE_LICENCE_GO = [
    '// Licensed under the Apache License, Version 2.0 (the "License");\n',
    '// you may not use this file except in compliance with the License.\n',
    '// You may obtain a copy of the License at\n',
    '//\n',
    '//      http://www.apache.org/licenses/LICENSE-2.0\n',
    '//\n',
    '// Unless required by applicable law or agreed to in writing, software\n',
    '// distributed under the License is distributed on an "AS IS" BASIS,\n',
    '// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.\n',
    '// See the License for the specific language governing permissions and\n',
    '// limitations under the License.\n',
    '\n'
]


def check_licence(file: str, fix: bool, lic: list[str]) -> bool:
    """Return False in case of empty licence"""
    try:
        with open(file, "r+", encoding="utf-8") as f:
            lines = f.readlines()
            if len(lines) < 10:
                if fix:
                    update_files(f, lines, lic)
                return False
            if (
                    (lines[0] == lic[0] and lines[10] == lic[10])
                    or (lines[1] == lic[0] and lines[11] == lic[10])
            ):
                return True
            if fix:
                update_files(f, lines, lic)
            return False
    except PermissionError:
        sys.stdout.write(f"file {file} unreachable \n")
        return False


def read_files(fixed: int, skipped: int, fix: bool, root: str = "") -> tuple[int, int]:
    root_path = Path(root)
    for path in os.listdir(root_path):
        lic = None
        path = os.path.join(root_path, path)
        if os.path.isdir(path):
            fixed, skipped = read_files(fixed, skipped, fix, path)
        if os.path.isfile(path):
            if path.endswith(".py"):
                lic = APACHE_LICENCE_PY
            elif path.endswith(".go") or path.endswith("go.mod"):
                lic = APACHE_LICENCE_GO
            if lic:
                if not check_licence(path, fix, lic):
                    sys.stdout.write(f"{path} has no license\n")
                    if fix:
                        fixed += 1
                    else:
                        skipped += 1
    return fixed, skipped


def update_files(f: TextIO, lines: list, lic: list[str]):
    lines.insert(0, "".join(lic))
    f.seek(0)
    f.writelines(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Checker for licence existing and fix it if need")
    parser.add_argument("--fix", nargs="?", const=True, default=False,
                        help="Flag to fix absent license in file (default will only find it)")
    parser.add_argument("--folders", nargs="+", help="Folders to check")
    args = parser.parse_args()
    number_of_fixed = number_of_skipped = 0
    for folder in args.folders:
        number_of_fixed, number_of_skipped = read_files(
            number_of_fixed, number_of_skipped, args.fix, folder
        )
    if number_of_fixed == number_of_skipped == 0:
        sys.stdout.write("Licence is present in all python and go files \n")
        sys.exit(0)
    sys.stdout.write(
        f"Updating licence skipped in {number_of_skipped} files."
        f" Licence was updated in {number_of_fixed} files \n"
    )
    sys.exit(1)
