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

import argparse
import io
import sys
from pathlib import Path

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


def has_licence(lines: list[str], lic: list[str]) -> bool:
    if (
            (lines[0] != lic[0] and lines[10] != lic[10])
            and (lines[1] != lic[0] and lines[11] != lic[11])
    ):
        return False

    return True


def write_license(lines: list[str], f: io.TextIOWrapper, lic: list[str]) -> None:
    lines.insert(0, "".join(lic))
    f.seek(0)
    f.writelines(lines)


def check_fix_files(root, fix: bool = False, skipped_counter: int = 0, fixed_counter: int = 0):
    # pylint: disable=too-many-branches

    for path in root.iterdir():
        if path.is_dir():
            skipped_counter, fixed_counter = check_fix_files(
                root=path,
                fix=fix,
                skipped_counter=skipped_counter,
                fixed_counter=fixed_counter,
            )

        str_path = str(path)
        py_need_to_check = str_path.endswith(".py")
        go_need_to_check = str_path.endswith(".go") or str_path.endswith("go.mod")
        if py_need_to_check or go_need_to_check:
            with open(path, "r+", encoding="utf-8") as f:
                lines = f.readlines()
                if len(lines) < 11:
                    sys.stdout.write(f"{path} has no license\n")

                    if not fix:
                        skipped_counter += 1
                        continue

                    if py_need_to_check:
                        lic = APACHE_LICENCE_PY
                    elif go_need_to_check:
                        lic = APACHE_LICENCE_GO

                    write_license(lines=lines, f=f, lic=lic)
                    fixed_counter += 1
                elif py_need_to_check:
                    if not has_licence(lines=lines, lic=APACHE_LICENCE_PY):
                        if not fix:
                            skipped_counter += 1
                            continue

                        sys.stdout.write(f"{path} has no license\n")
                        write_license(lines=lines, f=f, lic=APACHE_LICENCE_PY)
                        fixed_counter += 1
                elif go_need_to_check:
                    if not has_licence(lines, APACHE_LICENCE_GO):
                        if not fix:
                            skipped_counter += 1
                            continue

                        sys.stdout.write(f"{path} has no license\n")
                        write_license(lines=lines, f=f, lic=APACHE_LICENCE_GO)
                        fixed_counter += 1

    return skipped_counter, fixed_counter


def main():
    parser = argparse.ArgumentParser(
        description="Add Apache license 2.0 in the top of file if not exists. "
                    "Only check without args",
    )
    parser.add_argument("--folders", nargs="+", help="Folders to check")
    parser.add_argument("--fix", nargs="?", const=True, default=False,
                        help="Add license if not exists")
    args = parser.parse_args()
    sys.stdout.write("License checking started ...\n")

    skipped_counter = fixed_counter = 0
    for path in args.folders:
        skipped, fixed = check_fix_files(root=Path(".", path), fix=args.fix)
        skipped_counter += skipped
        fixed_counter += fixed

    sys.stdout.write(
        f"{skipped_counter} files skipped, {fixed_counter} files fixed. License checking finished\n"
    )


if __name__ == "__main__":
    main()
