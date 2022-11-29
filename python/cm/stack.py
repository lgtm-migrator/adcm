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
# pylint: disable=line-too-long,too-many-statements

import hashlib
import json
import re
import warnings
from copy import deepcopy
from pathlib import Path
from typing import Any

import ruyaml
import yaml
import yspec.checker
from django.conf import settings
from django.db import IntegrityError
from jinja2 import Template
from jinja2.exceptions import TemplateError
from rest_framework import status
from ruyaml.composer import ComposerError
from ruyaml.constructor import DuplicateKeyError
from ruyaml.error import ReusedAnchorWarning
from ruyaml.parser import ParserError as RuYamlParserError
from ruyaml.scanner import ScannerError as RuYamlScannerError
from version_utils import rpm
from yaml.parser import ParserError as YamlParserError
from yaml.scanner import ScannerError as YamlScannerError

from cm.adcm_config import (
    check_config_type,
    proto_ref,
    read_bundle_file,
    type_is_complex,
)
from cm.checker import FormatError, check, round_trip_load
from cm.errors import raise_adcm_ex
from cm.logger import logger
from cm.models import (
    StageAction,
    StagePrototype,
    StagePrototypeConfig,
    StagePrototypeExport,
    StagePrototypeImport,
    StageSubAction,
    StageUpgrade,
)

NAME_REGEX = r"[0-9a-zA-Z_\.-]+"


def save_definition(path: Path, fname: Path, conf, obj_list, bundle_hash, adcm_=False):
    if isinstance(conf, dict):
        save_object_definition(path, fname, conf, obj_list, bundle_hash, adcm_)
    else:
        for obj_def in conf:
            save_object_definition(path, fname, obj_def, obj_list, bundle_hash, adcm_)


def cook_obj_id(conf):
    return f"{conf['type']}.{conf['name']}.{conf['version']}"


def save_object_definition(path: Path, fname: Path, conf, obj_list, bundle_hash, adcm_=False):
    def_type = conf["type"]
    if def_type == "adcm" and not adcm_:
        return raise_adcm_ex("INVALID_OBJECT_DEFINITION", f'Invalid type "{def_type}" in object definition: {fname}')

    check_object_definition(fname=fname, conf=conf, def_type=def_type, obj_list=obj_list, bundle_hash=bundle_hash)
    obj = save_prototype(path, conf, def_type, bundle_hash)
    logger.info("Save definition of %s \"%s\" %s to stage", def_type, conf["name"], conf["version"])
    obj_list[cook_obj_id(conf)] = fname

    return obj


def check_actions_definition(def_type: str, actions: dict, bundle_hash: str):
    for action_name, action_data in actions.items():
        if action_name in {
            settings.ADCM_HOST_TURN_ON_MM_ACTION_NAME,
            settings.ADCM_HOST_TURN_OFF_MM_ACTION_NAME,
        }:
            if def_type != "cluster":
                raise_adcm_ex(
                    "INVALID_OBJECT_DEFINITION", f'Action named "{action_name}" can be started only in cluster context'
                )

            if not action_data.get("host_action"):
                raise_adcm_ex(
                    "INVALID_OBJECT_DEFINITION",
                    f'Action named "{action_name}" should have "host_action: true" property',
                )

        if action_name in settings.ADCM_SERVICE_ACTION_NAMES_SET and set(action_data).intersection(
            settings.ADCM_MM_ACTION_FORBIDDEN_PROPS_SET
        ):
            raise_adcm_ex(
                "INVALID_OBJECT_DEFINITION",
                f'Maintenance mode actions shouldn\'t have "{settings.ADCM_MM_ACTION_FORBIDDEN_PROPS_SET}" properties',
            )

        if action_data.get("config_jinja"):
            if action_data.get("config"):
                raise_adcm_ex(
                    "INVALID_OBJECT_DEFINITION", '"config" and "config_jinja" are mutually exclusive action options'
                )

            jinja_conf_file = Path(settings.BUNDLE_DIR, bundle_hash, action_data["config_jinja"])
            try:
                Template(jinja_conf_file.read_text(encoding=settings.ENCODING_UTF_8))
            except (FileNotFoundError, TemplateError) as e:
                raise_adcm_ex("INVALID_OBJECT_DEFINITION", str(e))


def check_object_definition(fname: Path, conf: dict, def_type: str, obj_list, bundle_hash: str | None = None):
    ref = f"{def_type} \"{conf['name']}\" {conf['version']}"
    if cook_obj_id(conf) in obj_list:
        raise_adcm_ex("INVALID_OBJECT_DEFINITION", f"Duplicate definition of {ref} (file {fname})")

    actions = conf.get("actions")
    if actions:
        check_actions_definition(def_type=def_type, actions=actions, bundle_hash=bundle_hash)


def get_config_files(path: Path):
    conf_list = []
    if not path.is_dir():
        raise_adcm_ex("STACK_LOAD_ERROR", f"no directory: {path}", status.HTTP_404_NOT_FOUND)

    for item in path.rglob("*"):
        if item.is_file() and item.name in {"config.yaml", "config.yml"}:
            conf_list.append((item.parent.name, item))

    if not conf_list:
        raise_adcm_ex("STACK_LOAD_ERROR", f"no config files in stack directory \"{path}\"")

    return conf_list


def check_adcm_config(conf_file: Path):
    warnings.simplefilter("error", ReusedAnchorWarning)
    schema_file = Path(settings.CODE_DIR, "cm", "adcm_schema.yaml")
    with open(schema_file, encoding=settings.ENCODING_UTF_8) as fd:
        rules = ruyaml.round_trip_load(fd)

    try:
        with open(conf_file, encoding=settings.ENCODING_UTF_8) as fd:
            data = round_trip_load(fd, version="1.1", allow_duplicate_keys=True)
    except (RuYamlParserError, RuYamlScannerError, NotImplementedError) as e:
        raise_adcm_ex("STACK_LOAD_ERROR", f"YAML decode \"{conf_file}\" error: {e}")
    except ruyaml.error.ReusedAnchorWarning as e:
        raise_adcm_ex("STACK_LOAD_ERROR", f"YAML decode \"{conf_file}\" error: {e}")
    except DuplicateKeyError as e:
        msg = f"{e.context}\n{e.context_mark}\n{e.problem}\n{e.problem_mark}"
        raise_adcm_ex("STACK_LOAD_ERROR", f"Duplicate Keys error: {msg}")
    except ComposerError as e:
        raise_adcm_ex("STACK_LOAD_ERROR", f"YAML Composer error: {e}")

    try:
        check(data, rules)
        return data
    except FormatError as e:
        args = ""
        if e.errors:
            for ee in e.errors:
                if "Input data for" in ee.message:
                    continue

                args += f"line {ee.line}: {ee}\n"

        raise_adcm_ex("INVALID_OBJECT_DEFINITION", f"\"{conf_file}\" line {e.line} error: {e}", args)

        return {}


def read_definition(conf_file: Path) -> dict:
    if conf_file.is_file():
        conf = check_adcm_config(conf_file)
        logger.info("Read config file: \"%s\"", conf_file)

        return conf

    logger.warning("Can not open config file: \"%s\"", conf_file)

    return {}


def get_license_hash(proto, conf, bundle_hash):
    if "license" not in conf:
        return None

    body = read_bundle_file(proto, conf["license"], bundle_hash, "license file")
    sha1 = hashlib.sha256()
    sha1.update(body.encode(settings.ENCODING_UTF_8))

    return sha1.hexdigest()


def process_config_group_customization(actual_config: dict, obj: StagePrototype):
    if not actual_config:
        return

    if "config_group_customization" not in actual_config:
        sp = None
        if obj.type == "service":
            try:
                sp = StagePrototype.objects.get(type="cluster")
            except StagePrototype.DoesNotExist:
                logger.debug("Can't find cluster for service %s", obj)

        if obj.type == "component":
            sp = obj.parent

        if sp:
            actual_config["config_group_customization"] = sp.config_group_customization


def save_prototype(path: Path, conf, def_type, bundle_hash):
    if path != bundle_hash:
        path = Path(bundle_hash, path)

    proto = StagePrototype(name=conf["name"], type=def_type, path=path, version=conf["version"])

    dict_to_obj(conf, "required", proto)
    dict_to_obj(conf, "shared", proto)
    dict_to_obj(conf, "monitoring", proto)
    dict_to_obj(conf, "display_name", proto)
    dict_to_obj(conf, "description", proto)
    dict_to_obj(conf, "adcm_min_version", proto)
    dict_to_obj(conf, "venv", proto)
    dict_to_obj(conf, "edition", proto)

    process_config_group_customization(conf, proto)

    dict_to_obj(conf, "config_group_customization", proto)
    dict_to_obj(conf, "allow_maintenance_mode", proto)

    fix_display_name(conf, proto)

    license_hash = get_license_hash(proto, conf, bundle_hash)
    if license_hash:
        if def_type not in ["cluster", "service", "provider"]:
            raise_adcm_ex(
                "INVALID_OBJECT_DEFINITION",
                f"Invalid license definition in {proto_ref(proto)}."
                f" License can be placed in cluster, service or provider",
            )

        proto.license_path = conf["license"]
        proto.license_hash = license_hash

    proto.save()

    save_actions(proto, conf, bundle_hash)
    save_upgrade(proto, conf, bundle_hash)
    save_components(proto, conf, bundle_hash)
    save_prototype_config(proto, conf, bundle_hash)
    save_export(proto, conf)
    save_import(proto, conf)

    return proto


def check_component_constraint(proto, name, conf):
    if not conf:
        return

    if "constraint" not in conf:
        return

    if len(conf["constraint"]) > 2:
        raise_adcm_ex(
            "INVALID_COMPONENT_DEFINITION",
            f"constraint of component \"{name}\" in {proto_ref(proto)} should have only 1 or 2 elements",
        )


def save_components(proto, conf, bundle_hash):
    ref = proto_ref(proto)
    if not in_dict(conf, "components"):
        return

    for comp_name in conf["components"]:
        cc = conf["components"][comp_name]
        validate_name(comp_name, f"Component name \"{comp_name}\" of {ref}")
        component = StagePrototype(
            type="component",
            parent=proto,
            path=proto.path,
            name=comp_name,
            version=proto.version,
            adcm_min_version=proto.adcm_min_version,
        )

        dict_to_obj(cc, "description", component)
        dict_to_obj(cc, "display_name", component)
        dict_to_obj(cc, "monitoring", component)

        fix_display_name(cc, component)
        check_component_constraint(proto, comp_name, cc)

        dict_to_obj(cc, "params", component)
        dict_to_obj(cc, "constraint", component)
        dict_to_obj(cc, "requires", component)
        dict_to_obj(cc, "venv", component)
        dict_to_obj(cc, "bound_to", component)

        process_config_group_customization(cc, component)

        dict_to_obj(cc, "config_group_customization", component)

        component.save()

        save_actions(component, cc, bundle_hash)
        save_prototype_config(component, cc, bundle_hash)


def check_upgrade(proto, conf):
    label = f"upgrade \"{conf['name']}\""
    check_versions(proto, conf, label)
    check_upgrade_scripts(proto, conf, label)


def check_upgrade_scripts(proto, conf, label):
    ref = proto_ref(proto)
    count = 0
    if "scripts" in conf:
        for action in conf["scripts"]:
            if action["script_type"] == "internal":
                count += 1
                if count > 1:
                    raise_adcm_ex(
                        "INVALID_UPGRADE_DEFINITION",
                        f"Script with script_type \"internal\" must be unique in {label} of {ref}",
                    )

                if action["script"] != "bundle_switch":
                    raise_adcm_ex(
                        "INVALID_UPGRADE_DEFINITION",
                        f"Script with script_type \"internal\" should be marked "
                        f"as \"bundle_switch\" in {label} of {ref}",
                    )

        if count == 0:
            raise_adcm_ex(
                "INVALID_UPGRADE_DEFINITION",
                f"Scripts block in {label} of {ref} must contain exact one block with script \"bundle_switch\"",
            )
    else:
        if "masking" in conf or "on_success" in conf or "on_fail" in conf:
            raise_adcm_ex(
                "INVALID_UPGRADE_DEFINITION",
                f"{label} of {ref} couldn't contain `masking`, `on_success` or `on_fail` without `scripts` block",
            )


def check_versions(proto, conf, label):
    ref = proto_ref(proto)
    if "min" in conf["versions"] and "min_strict" in conf["versions"]:
        raise_adcm_ex(
            "INVALID_VERSION_DEFINITION",
            f"min and min_strict can not be used simultaneously in versions of {label} ({ref})",
        )

    if "min" not in conf["versions"] and "min_strict" not in conf["versions"] and "import" not in label:
        raise_adcm_ex(
            "INVALID_VERSION_DEFINITION",
            f"min or min_strict should be present in versions of {label} ({ref})",
        )

    if "max" in conf["versions"] and "max_strict" in conf["versions"]:
        raise_adcm_ex(
            "INVALID_VERSION_DEFINITION",
            f"max and max_strict can not be used simultaneously in versions of {label} ({ref})",
        )

    if "max" not in conf["versions"] and "max_strict" not in conf["versions"] and "import" not in label:
        raise_adcm_ex(
            "INVALID_VERSION_DEFINITION",
            f"max and max_strict should be present in versions of {label} ({ref})",
        )

    for name in ("min", "min_strict", "max", "max_strict"):
        if name in conf["versions"] and not conf["versions"][name]:
            raise_adcm_ex("INVALID_VERSION_DEFINITION", f"{name} versions of {label} should be not null ({ref})")


def set_version(obj, conf):
    if "min" in conf["versions"]:
        obj.min_version = conf["versions"]["min"]
        obj.min_strict = False
    elif "min_strict" in conf["versions"]:
        obj.min_version = conf["versions"]["min_strict"]
        obj.min_strict = True

    if "max" in conf["versions"]:
        obj.max_version = conf["versions"]["max"]
        obj.max_strict = False
    elif "max_strict" in conf["versions"]:
        obj.max_version = conf["versions"]["max_strict"]
        obj.max_strict = True


def save_upgrade(proto, conf, bundle_hash):
    if not in_dict(conf, "upgrade"):
        return

    for item in conf["upgrade"]:
        check_upgrade(proto, item)
        upg = StageUpgrade(name=item["name"])
        set_version(upg, item)
        dict_to_obj(item, "description", upg)
        if "states" in item:
            dict_to_obj(item["states"], "available", upg)
            if "available" in item["states"]:
                upg.state_available = item["states"]["available"]

            if "on_success" in item["states"]:
                upg.state_on_success = item["states"]["on_success"]

        if in_dict(item, "from_edition"):
            upg.from_edition = item["from_edition"]

        if "scripts" in item:
            upg.action = save_actions(proto, item, bundle_hash, upg)

        upg.save()


def save_export(proto, conf):
    ref = proto_ref(proto)
    if not in_dict(conf, "export"):
        return

    export = {}
    if isinstance(conf["export"], str):
        export = [conf["export"]]
    elif isinstance(conf["export"], list):
        export = conf["export"]

    for key in export:
        if not StagePrototypeConfig.objects.filter(prototype=proto, name=key):
            raise_adcm_ex("INVALID_OBJECT_DEFINITION", f'{ref} does not has "{key}" config group')

        stage_prototype_export = StagePrototypeExport(prototype=proto, name=key)
        stage_prototype_export.save()


def get_config_groups(proto, action=None):
    groups = {}
    for stage_prototype_config in StagePrototypeConfig.objects.filter(prototype=proto, action=action):
        if stage_prototype_config.subname != "":
            groups[stage_prototype_config.name] = stage_prototype_config.name

    return groups


def check_default_import(proto, conf):
    ref = proto_ref(proto)
    if "default" not in conf:
        return

    groups = get_config_groups(proto)
    for key in conf["default"]:
        if key not in groups:
            raise_adcm_ex("INVALID_OBJECT_DEFINITION", f"No import default group \"{key}\" in config ({ref})")


def save_import(proto, conf):
    ref = proto_ref(proto)
    if not in_dict(conf, "import"):
        return

    for key in conf["import"]:
        if "default" in conf["import"][key] and "required" in conf["import"][key]:
            raise_adcm_ex(
                "INVALID_OBJECT_DEFINITION",
                f"Import can't have default and be required in the same time ({ref})",
            )

        check_default_import(proto, conf["import"][key])
        stage_prototype_import = StagePrototypeImport(prototype=proto, name=key)
        if "versions" in conf["import"][key]:
            check_versions(proto, conf["import"][key], f"import \"{key}\"")
            set_version(stage_prototype_import, conf["import"][key])
            if stage_prototype_import.min_version and stage_prototype_import.max_version:
                if (
                    rpm.compare_versions(
                        str(stage_prototype_import.min_version), str(stage_prototype_import.max_version)
                    )
                    > 0
                ):
                    raise_adcm_ex("INVALID_VERSION_DEFINITION", "Min version should be less or equal max version")

        dict_to_obj(conf["import"][key], "required", stage_prototype_import)
        dict_to_obj(conf["import"][key], "multibind", stage_prototype_import)
        dict_to_obj(conf["import"][key], "default", stage_prototype_import)

        stage_prototype_import.save()


def check_action_hc(proto, conf):
    if "hc_acl" not in conf:
        return

    for idx, item in enumerate(conf["hc_acl"]):
        if "service" not in item:
            if proto.type == "service":
                item["service"] = proto.name
                conf["hc_acl"][idx]["service"] = proto.name


def save_sub_actions(conf, action):
    if action.type != "task":
        return

    for sub in conf["scripts"]:
        sub_action = StageSubAction(
            action=action, script=sub["script"], script_type=sub["script_type"], name=sub["name"]
        )
        sub_action.display_name = sub["name"]

        if "display_name" in sub:
            sub_action.display_name = sub["display_name"]

        dict_to_obj(sub, "params", sub_action)
        on_fail = sub.get(ON_FAIL, "")
        if isinstance(on_fail, str):
            sub_action.state_on_fail = on_fail
            sub_action.multi_state_on_fail_set = []
            sub_action.multi_state_on_fail_unset = []
        elif isinstance(on_fail, dict):
            sub_action.state_on_fail = _deep_get(on_fail, STATE, default="")
            sub_action.multi_state_on_fail_set = _deep_get(on_fail, MULTI_STATE, SET, default=[])
            sub_action.multi_state_on_fail_unset = _deep_get(on_fail, MULTI_STATE, UNSET, default=[])

        sub_action.save()


MASKING = "masking"
STATES = "states"
STATE = "state"
MULTI_STATE = "multi_state"
AVAILABLE = "available"
UNAVAILABLE = "unavailable"
ON_SUCCESS = "on_success"
ON_FAIL = "on_fail"
ANY = "any"
SET = "set"
UNSET = "unset"


def save_actions(proto, conf, bundle_hash, upgrade: StageUpgrade | None = None):
    if in_dict(conf, "versions"):
        conf["type"] = "task"
        upgrade_name = conf["name"]
        conf["display_name"] = f"Upgrade: {upgrade_name}"

        if upgrade is not None:
            action_name = (
                f"{proto.name}_{proto.version}_{proto.edition}_upgrade_{upgrade_name}_{upgrade.min_version}_strict_"
                f"{upgrade.min_strict}-{upgrade.max_version}_strict_{upgrade.min_strict}_editions-"
                f"{'_'.join(upgrade.from_edition)}_state_available-{'_'.join(upgrade.state_available)}_"
                f"state_on_success-{upgrade.state_on_success}"
            )
        else:
            action_name = f"{proto.name}_{proto.version}_{proto.edition}_upgrade_{upgrade_name}"

        action_name = re.sub(r"\s+", "_", action_name).strip().lower()
        action_name = re.sub(r"[()]", "", action_name)
        upgrade_action = save_action(proto, conf, bundle_hash, action_name)

        return upgrade_action

    if not in_dict(conf, "actions"):
        return None

    for action_name in sorted(conf["actions"]):
        ac = conf["actions"][action_name]
        save_action(proto, ac, bundle_hash, action_name)

    return None


def save_action(proto, ac, bundle_hash, action_name):
    validate_name(action_name, f"Action name \"{action_name}\" of {proto.type} \"{proto.name}\" {proto.version}")
    action = StageAction(prototype=proto, name=action_name)
    action.type = ac["type"]

    if ac["type"] == "job":
        action.script = ac["script"]
        action.script_type = ac["script_type"]

    dict_to_obj(ac, "display_name", action)
    dict_to_obj(ac, "description", action)
    dict_to_obj(ac, "allow_to_terminate", action)
    dict_to_obj(ac, "partial_execution", action)
    dict_to_obj(ac, "host_action", action)
    dict_to_obj(ac, "ui_options", action)
    dict_to_obj(ac, "params", action)
    dict_to_obj(ac, "log_files", action)
    dict_to_obj(ac, "venv", action)
    dict_to_obj(ac, "allow_in_maintenance_mode", action)
    dict_to_obj(ac, "config_jinja", action)

    fix_display_name(ac, action)
    check_action_hc(proto, ac)
    dict_to_obj(ac, "hc_acl", action, "hostcomponentmap")

    if MASKING in ac:
        if STATES in ac:
            raise_adcm_ex(
                "INVALID_OBJECT_DEFINITION",
                f"Action {action_name} uses both mutual excluding states \"states\" and \"masking\"",
            )

        action.state_available = _deep_get(ac, MASKING, STATE, AVAILABLE, default=ANY)
        action.state_unavailable = _deep_get(ac, MASKING, STATE, UNAVAILABLE, default=[])
        action.state_on_success = _deep_get(ac, ON_SUCCESS, STATE, default="")
        action.state_on_fail = _deep_get(ac, ON_FAIL, STATE, default="")

        action.multi_state_available = _deep_get(ac, MASKING, MULTI_STATE, AVAILABLE, default=ANY)
        action.multi_state_unavailable = _deep_get(ac, MASKING, MULTI_STATE, UNAVAILABLE, default=[])
        action.multi_state_on_success_set = _deep_get(ac, ON_SUCCESS, MULTI_STATE, SET, default=[])
        action.multi_state_on_success_unset = _deep_get(ac, ON_SUCCESS, MULTI_STATE, UNSET, default=[])
        action.multi_state_on_fail_set = _deep_get(ac, ON_FAIL, MULTI_STATE, SET, default=[])
        action.multi_state_on_fail_unset = _deep_get(ac, ON_FAIL, MULTI_STATE, UNSET, default=[])
    else:
        if ON_SUCCESS in ac or ON_FAIL in ac:
            raise_adcm_ex(
                "INVALID_OBJECT_DEFINITION",
                f"Action {action_name} uses \"on_success/on_fail\" states without \"masking\"",
            )

        action.state_available = _deep_get(ac, STATES, AVAILABLE, default=[])
        action.state_unavailable = []
        action.state_on_success = _deep_get(ac, STATES, ON_SUCCESS, default="")
        action.state_on_fail = _deep_get(ac, STATES, ON_FAIL, default="")

        action.multi_state_available = ANY
        action.multi_state_unavailable = []
        action.multi_state_on_success_set = []
        action.multi_state_on_success_unset = []
        action.multi_state_on_fail_set = []
        action.multi_state_on_fail_unset = []

    action.save()
    save_sub_actions(ac, action)
    save_prototype_config(proto, ac, bundle_hash, action)

    return action


def get_yspec(proto, bundle_hash, conf, name, subname):
    schema = None
    yspec_body = read_bundle_file(proto, conf["yspec"], bundle_hash, f'yspec file of config key "{name}/{subname}":')
    try:
        schema = yaml.safe_load(yspec_body)
    except (YamlParserError, YamlScannerError) as e:
        raise_adcm_ex("CONFIG_TYPE_ERROR", f'yspec file of config key "{name}/{subname}" yaml decode error: {e}')

    ok, error = yspec.checker.check_rule(schema)
    if not ok:
        raise_adcm_ex("CONFIG_TYPE_ERROR", f'yspec file of config key "{name}/{subname}" error: {error}')

    return schema


def save_prototype_config(
    proto, proto_conf, bundle_hash, action=None
):  # pylint: disable=too-many-statements,too-many-locals
    if not in_dict(proto_conf, "config"):
        return

    conf_dict = proto_conf["config"]
    ref = proto_ref(proto)

    def check_variant(_conf):
        vtype = _conf["source"]["type"]
        source = {"type": vtype, "args": None}
        if "strict" in _conf["source"]:
            source["strict"] = _conf["source"]["strict"]
        else:
            source["strict"] = True

        if vtype == "inline":
            source["value"] = _conf["source"]["value"]
        elif vtype in ("config", "builtin"):
            source["name"] = _conf["source"]["name"]

        if vtype == "builtin":
            if "args" in _conf["source"]:
                source["args"] = _conf["source"]["args"]

        return source

    def process_limits(_conf, _name, _subname):
        opt = {}
        if _conf["type"] == "option":
            opt = {"option": _conf["option"]}
        elif _conf["type"] == "variant":
            opt["source"] = check_variant(_conf)
        elif _conf["type"] == "integer" or _conf["type"] == "float":
            if "min" in _conf:
                opt["min"] = _conf["min"]
            if "max" in _conf:
                opt["max"] = _conf["max"]
        elif _conf["type"] == "structure":
            opt["yspec"] = get_yspec(proto, bundle_hash, _conf, _name, _subname)
        elif _conf["type"] == "group":
            if "activatable" in _conf:
                opt["activatable"] = _conf["activatable"]
                opt["active"] = False
                if "active" in _conf:
                    opt["active"] = _conf["active"]

        if "read_only" in _conf and "writable" in _conf:
            key_ref = f"(config key \"{_name}/{_subname}\" of {ref})"
            msg = "can not have \"read_only\" and \"writable\" simultaneously {}"
            raise_adcm_ex("INVALID_CONFIG_DEFINITION", msg.format(key_ref))

        for label in ("read_only", "writable"):
            if label in _conf:
                opt[label] = _conf[label]

        return opt

    def cook_conf(obj, _conf, _name, _subname):
        stage_prototype_config = StagePrototypeConfig(prototype=obj, action=action, name=_name, type=_conf["type"])

        dict_to_obj(_conf, "description", stage_prototype_config)
        dict_to_obj(_conf, "display_name", stage_prototype_config)
        dict_to_obj(_conf, "required", stage_prototype_config)
        dict_to_obj(_conf, "ui_options", stage_prototype_config)
        dict_to_obj(_conf, "group_customization", stage_prototype_config)

        _conf["limits"] = process_limits(_conf, _name, _subname)
        dict_to_obj(_conf, "limits", stage_prototype_config)

        if "display_name" not in _conf:
            if _subname:
                stage_prototype_config.display_name = _subname
            else:
                stage_prototype_config.display_name = _name

        if "default" in _conf:
            check_config_type(proto, _name, _subname, _conf, _conf["default"], bundle_hash)

        if type_is_complex(_conf["type"]):
            dict_json_to_obj(_conf, "default", stage_prototype_config)
        else:
            dict_to_obj(_conf, "default", stage_prototype_config)

        if _subname:
            stage_prototype_config.subname = _subname

        try:
            stage_prototype_config.save()
        except IntegrityError:
            raise_adcm_ex(
                "INVALID_CONFIG_DEFINITION",
                f"Duplicate config on {obj.type} {obj}, action {action}, with name {_name} and subname {_subname}",
            )

    if isinstance(conf_dict, dict):
        for name, conf in conf_dict.items():
            if "type" in conf:
                validate_name(name, f"Config key \"{name}\" of {ref}")
                cook_conf(proto, conf, name, "")
            else:
                validate_name(name, f"Config group \"{name}\" of {ref}")
                group_conf = {"type": "group", "required": False}
                cook_conf(proto, group_conf, name, "")
                for (subname, subconf) in conf.items():
                    err_msg = f"Config key \"{name}/{subname}\" of {ref}"
                    validate_name(name, err_msg)
                    validate_name(subname, err_msg)
                    cook_conf(proto, subconf, name, subname)

    elif isinstance(conf_dict, list):
        for conf in conf_dict:
            name = conf["name"]
            validate_name(name, f"Config key \"{name}\" of {ref}")
            cook_conf(proto, conf, name, "")
            if conf["type"] == "group":
                for subconf in conf["subs"]:
                    subname = subconf["name"]
                    err_msg = f"Config key \"{name}/{subname}\" of {ref}"
                    validate_name(name, err_msg)
                    validate_name(subname, err_msg)
                    cook_conf(proto, subconf, name, subname)


def validate_name(value, err_msg):
    if not isinstance(value, str):
        raise_adcm_ex("WRONG_NAME", f"{err_msg} should be string")

    p = re.compile(NAME_REGEX)
    msg1 = "{} is incorrect. Only latin characters, digits, dots (.), dashes (-), and underscores (_) are allowed."
    if p.fullmatch(value) is None:
        raise_adcm_ex("WRONG_NAME", msg1.format(err_msg))

    return value


def fix_display_name(conf, obj):
    if isinstance(conf, dict) and "display_name" in conf:
        return

    obj.display_name = obj.name


def in_dict(dictionary, key):
    if not isinstance(dictionary, dict):
        return False

    if key in dictionary:
        if dictionary[key] is None:
            return False
        else:
            return True
    else:
        return False


def dict_to_obj(dictionary, key, obj, obj_key=None):
    if not obj_key:
        obj_key = key

    if not isinstance(dictionary, dict):
        return

    if key in dictionary:
        if dictionary[key] is not None:
            setattr(obj, obj_key, dictionary[key])


def dict_json_to_obj(dictionary, key, obj, obj_key=""):
    if obj_key == "":
        obj_key = key

    if isinstance(dictionary, dict):
        if key in dictionary:
            setattr(obj, obj_key, json.dumps(dictionary[key]))


def _deep_get(deep_dict: dict, *nested_keys: str, default: Any) -> Any:
    """
    Safe dict.get() for deep-nested dictionaries
    dct[key1][key2][...] -> _deep_get(dct, key1, key2, ..., default_value)
    """

    val = deepcopy(deep_dict)
    for key in nested_keys:
        try:
            val = val[key]
        except (KeyError, TypeError):
            return default

    return val
