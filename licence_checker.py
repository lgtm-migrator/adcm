import sys
import os

APACHE_LICENCE = ['Licensed under the Apache License, Version 2.0 (the "License");',
                  "you may not use this file except in compliance with the License.",
                  "You may obtain a copy of the License at",
                  "",
                  "     http://www.apache.org/licenses/LICENSE-2.0",
                  "",
                  "Unless required by applicable law or agreed to in writing, software",
                  'distributed under the License is distributed on an "AS IS" BASIS,',
                  "WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.",
                  "See the License for the specific language governing permissions and",
                  "limitations under the License."]


def check_licence(file):
    """Return False in case of empty licence"""
    with open(file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        if len(lines) < 10:
            return False
        if (lines[0].find(APACHE_LICENCE[0]) != -1) or (lines[1].find(APACHE_LICENCE[0]) != -1):
            if (lines[10].find(APACHE_LICENCE[10]) != -1) \
                    or (lines[11].find(APACHE_LICENCE[10]) != -1):
                return True
        return False


def read_files(root: str = ""):
    root_path = os.path.join(root)
    result = []
    for path in os.listdir(root_path):
        path = os.path.join(root_path, path)
        if os.path.isdir(path):
            result.extend(read_files(path))
        if os.path.isfile(path) and (
                path.endswith(".py") or path.endswith(".go") or path.endswith("go.mod")
        ):
            if not check_licence(path):
                result.append(path)
    return result


def update_files(files_to_update: list):
    new_line = "\n"
    for file in files_to_update:
        separator = "# " if file.endswith(".py") else "// "
        with open(file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        with open(file, "w", encoding="utf-8") as f:
            lines.insert(0, f'{separator}{f"{new_line}{separator}".join(APACHE_LICENCE)}{new_line}')
            f.writelines(lines)


if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__))
    empty_licence = []
    for name in ["python", "go", "tests"]:
        empty_licence.extend(read_files(name))
    if len(sys.argv) < 2:
        if empty_licence:
            sys.stdout.write(
                f"Licence not detected in the following files: {', '.join(empty_licence)} \n"
            )
            sys.exit(1)
        else:
            sys.stdout.write("Licence is present in all python and go files \n")
            sys.exit(0)
    else:
        if sys.argv[1] == "--fix" and empty_licence:
            if empty_licence:
                sys.stdout.write(
                    f"Following files will be updated with the "
                    f"licence {', '.join(empty_licence)} \n"
                )
                update_files(empty_licence)
                sys.exit(1)
            sys.stdout.write("Licence is present in all python and go files \n")
            sys.exit(0)
        else:
            sys.stdout.write(f"Unxpected script parameter {sys.argv[1]}. Only `--fix` approach \n")
            sys.exit(1)
