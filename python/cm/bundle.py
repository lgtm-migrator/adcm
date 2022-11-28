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
# pylint: disable=too-many-lines

import functools
import hashlib
import shutil
import tarfile
from pathlib import Path

from django.conf import settings
from django.db import IntegrityError, transaction
from version_utils import rpm

import cm.stack
import cm.status_api
from cm.adcm_config import init_object_config, proto_ref, switch_config
from cm.errors import raise_adcm_ex as err
from cm.logger import logger
from cm.models import (
    ADCM,
    Action,
    Bundle,
    Cluster,
    HostProvider,
    ProductCategory,
    Prototype,
    PrototypeConfig,
    PrototypeExport,
    PrototypeImport,
    StageAction,
    StagePrototype,
    StagePrototypeConfig,
    StagePrototypeExport,
    StagePrototypeImport,
    StageSubAction,
    StageUpgrade,
    SubAction,
    Upgrade,
)
from rbac.models import Role
from rbac.upgrade.role import prepare_action_roles

STAGE = (
    StagePrototype,
    StageAction,
    StagePrototypeConfig,
    StageUpgrade,
    StagePrototypeExport,
    StagePrototypeImport,
)


def load_bundle(bundle_file):
    logger.info('loading bundle file "%s" ...', bundle_file)
    bundle_hash, path = process_file(bundle_file)

    try:
        check_stage()
        process_bundle(path, bundle_hash)
        bundle_proto = get_stage_bundle(bundle_file)
        second_pass()
    except Exception:
        clear_stage()
        shutil.rmtree(path)
        raise

    try:
        bundle = copy_stage(bundle_hash, bundle_proto)
        order_versions()
        clear_stage()
        ProductCategory.re_collect()
        bundle.refresh_from_db()
        prepare_action_roles(bundle)
        cm.status_api.post_event("create", "bundle", bundle.id)
        return bundle
    except Exception:
        clear_stage()
        raise


def update_bundle(bundle):
    try:
        check_stage()
        process_bundle(settings.BUNDLE_DIR / bundle.hash, bundle.hash)
        get_stage_bundle(bundle.name)
        second_pass()
        update_bundle_from_stage(bundle)
        order_versions()
        clear_stage()
    except:
        clear_stage()
        raise


def order_model_versions(model):
    items = []
    for obj in model.objects.all():
        items.append(obj)
    ver = ""
    count = 0
    for obj in sorted(
        items,
        key=functools.cmp_to_key(lambda obj1, obj2: rpm.compare_versions(obj1.version, obj2.version)),
    ):
        if ver != obj.version:
            count += 1
        obj.version_order = count
        ver = obj.version
    # Update all table in one time. That is much faster than one by one method
    model.objects.bulk_update(items, ["version_order"])


def order_versions():
    order_model_versions(Prototype)
    order_model_versions(Bundle)


def process_file(bundle_file):
    path = str(settings.DOWNLOAD_DIR / bundle_file)
    bundle_hash = get_hash_safe(path)
    dir_path = untar_safe(bundle_hash, path)
    return (bundle_hash, dir_path)


def untar_safe(bundle_hash: str, path: str) -> str:
    dir_path = None

    try:
        dir_path = untar(bundle_hash, path)
    except tarfile.ReadError:
        err("BUNDLE_ERROR", f"Can't open bundle tar file: {path}")

    return dir_path


def untar(bundle_hash, bundle):
    path = settings.BUNDLE_DIR / bundle_hash
    if path.is_dir():
        try:
            existed = Bundle.objects.get(hash=bundle_hash)
            msg = "Bundle already exists. Name: {}, version: {}, edition: {}"
            err(
                "BUNDLE_ERROR",
                msg.format(existed.name, existed.version, existed.edition),
            )
        except Bundle.DoesNotExist:
            logger.warning(
                (
                    f"There is no bundle with hash {bundle_hash} in DB, ",
                    "but there is a dir on disk with this hash. Dir will be overwritten.",
                )
            )
    tar = tarfile.open(bundle)
    tar.extractall(path=path)
    tar.close()

    return path


def get_hash_safe(path: str) -> str:
    bundle_hash = None

    try:
        bundle_hash = get_hash(path)
    except FileNotFoundError:
        err("BUNDLE_ERROR", f"Can't find bundle file: {path}")
    except PermissionError:
        err("BUNDLE_ERROR", f"Can't open bundle file: {path}")

    return bundle_hash


def get_hash(bundle_file: str) -> str:
    sha1 = hashlib.sha1()
    with open(bundle_file, "rb") as fp:
        for data in iter(lambda: fp.read(16384), b""):
            sha1.update(data)

    return sha1.hexdigest()


def load_adcm():
    check_stage()
    adcm_file = settings.BASE_DIR / "conf" / "adcm" / "config.yaml"
    conf = cm.stack.read_definition(adcm_file, "yaml")
    if not conf:
        logger.warning("Empty adcm config (%s)", adcm_file)
        return

    try:
        cm.stack.save_definition("", adcm_file, conf, {}, "adcm", True)
        process_adcm()
    except Exception:
        clear_stage()

        raise

    clear_stage()


def process_adcm():
    adcm_stage_proto = StagePrototype.objects.get(type="adcm")
    adcm = ADCM.objects.filter()
    if adcm:
        old_proto = adcm[0].prototype
        new_proto = adcm_stage_proto
        if old_proto.version == new_proto.version:
            logger.debug("adcm version %s, skip upgrade", old_proto.version)
        elif rpm.compare_versions(old_proto.version, new_proto.version) < 0:
            bundle = copy_stage("adcm", adcm_stage_proto)
            upgrade_adcm(adcm[0], bundle)
        else:
            err(
                "UPGRADE_ERROR",
                f"Current adcm version {old_proto.version} is more than "
                f"or equal to upgrade version {new_proto.version}",
            )
    else:
        bundle = copy_stage("adcm", adcm_stage_proto)
        init_adcm(bundle)


def init_adcm(bundle):
    proto = Prototype.objects.get(type="adcm", bundle=bundle)
    with transaction.atomic():
        adcm = ADCM.objects.create(prototype=proto, name="ADCM")
        obj_conf = init_object_config(proto, adcm)
        adcm.config = obj_conf
        adcm.save()

    logger.info("init adcm object version %s OK", proto.version)

    return adcm


def upgrade_adcm(adcm, bundle):
    old_proto = adcm.prototype
    new_proto = Prototype.objects.get(type="adcm", bundle=bundle)
    if rpm.compare_versions(old_proto.version, new_proto.version) >= 0:
        err(
            "UPGRADE_ERROR",
            f"Current adcm version {old_proto.version} is more than or equal to upgrade version {new_proto.version}",
        )

    with transaction.atomic():
        adcm.prototype = new_proto
        adcm.save()
        switch_config(adcm, new_proto, old_proto)

    logger.info(
        "upgrade adcm OK from version %s to %s",
        old_proto.version,
        adcm.prototype.version,
    )

    return adcm


def process_bundle(path, bundle_hash):
    obj_list = {}
    for conf_path, conf_file, conf_type in cm.stack.get_config_files(path, bundle_hash):
        conf = cm.stack.read_definition(conf_file, conf_type)
        if conf:
            cm.stack.save_definition(conf_path, conf_file, conf, obj_list, bundle_hash)


def check_stage():
    def count(_model):
        if _model.objects.all().count():
            err("BUNDLE_ERROR", f"Stage is not empty {_model}")

    for model in STAGE:
        count(model)


def copy_obj(orig, clone, fields):
    obj = clone()
    for f in fields:
        setattr(obj, f, getattr(orig, f))

    return obj


def update_obj(dest, source, fields):
    for f in fields:
        setattr(dest, f, getattr(source, f))


def re_check_actions():
    for act in StageAction.objects.all():
        if not act.hostcomponentmap:
            continue

        hc = act.hostcomponentmap
        ref = f'in hc_acl of action "{act.name}" of {proto_ref(act.prototype)}'
        for item in hc:
            stage_proto = StagePrototype.objects.filter(type="service", name=item["service"]).first()
            if not stage_proto:
                err(
                    "INVALID_ACTION_DEFINITION",
                    f'Unknown service "{item["service"]}" {ref}',
                )

            if not StagePrototype.objects.filter(parent=stage_proto, type="component", name=item["component"]):
                err(
                    "INVALID_ACTION_DEFINITION",
                    f'Unknown component "{item["component"]}" of service "{stage_proto.name}" {ref}',
                )


def check_component_requires(comp):
    if not comp.requires:
        return

    req_list = comp.requires
    for i, item in enumerate(req_list):
        if "service" in item:
            service = StagePrototype.obj.get(name=item["service"], type="service")
        else:
            service = comp.parent
            req_list[i]["service"] = comp.parent.name

        req_comp = StagePrototype.obj.get(name=item["component"], type="component", parent=service)
        if comp == req_comp:
            err(
                "COMPONENT_CONSTRAINT_ERROR",
                f'Component can not require themself in requires of component '
                f'"{comp.name}" of {proto_ref(comp.parent)}',
            )

    comp.requires = req_list
    comp.save()


def check_bound_component(comp):
    if not comp.bound_to:
        return

    bind = comp.bound_to
    service = StagePrototype.obj.get(name=bind["service"], type="service")
    bind_comp = StagePrototype.obj.get(name=bind["component"], type="component", parent=service)
    if comp == bind_comp:
        err(
            "COMPONENT_CONSTRAINT_ERROR",
            f'Component can not require themself in "bound_to" of component "{comp.name}" of {proto_ref(comp.parent)}',
        )


def re_check_components():
    for comp in StagePrototype.objects.filter(type="component"):
        check_component_requires(comp)
        check_bound_component(comp)


def check_variant_host(args, ref):
    def check_predicate(predicate, _args):
        if predicate == "in_service":
            StagePrototype.obj.get(type="service", name=_args["service"])
        elif predicate == "in_component":
            service = StagePrototype.obj.get(type="service", name=_args["service"])
            StagePrototype.obj.get(type="component", name=_args["component"], parent=service)

    if args is None:
        return

    if isinstance(args, dict):
        if "predicate" not in args:
            return

        check_predicate(args["predicate"], args["args"])
        check_variant_host(args["args"], ref)

    if isinstance(args, list):
        for i in args:
            check_predicate(i["predicate"], i["args"])
            check_variant_host(i["args"], ref)


def re_check_config():
    sp_service = None
    same_stage_prototype_config = None

    for stage_prototype_config in StagePrototypeConfig.objects.filter(type="variant"):
        ref = proto_ref(stage_prototype_config.prototype)
        lim = stage_prototype_config.limits
        if lim["source"]["type"] == "list":
            keys = lim["source"]["name"].split("/")
            name = keys[0]
            subname = ""
            if len(keys) > 1:
                subname = keys[1]

            try:
                same_stage_prototype_config = StagePrototypeConfig.objects.get(
                    prototype=stage_prototype_config.prototype,
                    name=name,
                    subname=subname,
                )
            except StagePrototypeConfig.DoesNotExist:
                err(
                    "INVALID_CONFIG_DEFINITION",
                    f'Unknown config source name "{lim["source"]["name"]}" for {ref} config '
                    f'"{stage_prototype_config.name}/{stage_prototype_config.subname}"',
                )

            if same_stage_prototype_config == stage_prototype_config:
                err(
                    "INVALID_CONFIG_DEFINITION",
                    f'Config parameter "{stage_prototype_config.name}/{stage_prototype_config.subname}" '
                    f'can not refer to itself ({ref})',
                )
        elif lim["source"]["type"] == "builtin":
            if not lim["source"]["args"]:
                continue

            if lim["source"]["name"] == "host":
                check_variant_host(
                    lim["source"]["args"],
                    f'in source:args of {ref} config "{stage_prototype_config.name}/{stage_prototype_config.subname}"',
                )

            if "service" in lim["source"]["args"]:
                service = lim["source"]["args"]["service"]
                try:
                    sp_service = StagePrototype.objects.get(type="service", name=service)
                except StagePrototype.DoesNotExist:
                    err(
                        "INVALID_CONFIG_DEFINITION",
                        f'Service "{service}" in source:args of {ref} config '
                        f'"{stage_prototype_config.name}/{stage_prototype_config.subname}" does not exists',
                    )

            if "component" in lim["source"]["args"]:
                comp = lim["source"]["args"]["component"]
                try:
                    StagePrototype.objects.get(type="component", name=comp, parent=sp_service)
                except StagePrototype.DoesNotExist:
                    err(
                        "INVALID_CONFIG_DEFINITION",
                        f'Component "{comp}" in source:args of {ref} config '
                        f'"{stage_prototype_config.name}/{stage_prototype_config.subname}" does not exists',
                    )


def second_pass():
    re_check_actions()
    re_check_components()
    re_check_config()


def copy_stage_prototype(stage_prototypes, bundle):
    prototypes = []  # Map for stage prototype id: new prototype
    for sp in stage_prototypes:
        proto = copy_obj(
            sp,
            Prototype,
            (
                "type",
                "path",
                "name",
                "version",
                "required",
                "shared",
                "license_path",
                "license_hash",
                "monitoring",
                "display_name",
                "description",
                "adcm_min_version",
                "venv",
                "config_group_customization",
                "allow_maintenance_mode",
            ),
        )
        if proto.license_path:
            proto.license = "unaccepted"
            if check_license(proto):
                proto.license = "accepted"

        proto.bundle = bundle
        prototypes.append(proto)

    Prototype.objects.bulk_create(prototypes)


def copy_stage_upgrade(stage_upgrades, bundle):
    upgrades = []
    for su in stage_upgrades:
        upg = copy_obj(
            su,
            Upgrade,
            (
                "name",
                "description",
                "min_version",
                "max_version",
                "min_strict",
                "max_strict",
                "state_available",
                "state_on_success",
                "from_edition",
            ),
        )
        upg.bundle = bundle
        upgrades.append(upg)
        if su.action:
            prototype = Prototype.objects.get(name=su.action.prototype.name, bundle=bundle)
            upg.action = Action.objects.get(prototype=prototype, name=su.action.name)

    Upgrade.objects.bulk_create(upgrades)


def prepare_bulk(origin_objects, target, prototype, fields):
    target_objects = []
    for oo in origin_objects:
        to = copy_obj(oo, target, fields)
        to.prototype = prototype
        target_objects.append(to)

    return target_objects


def copy_stage_actions(stage_actions, prototype):
    actions = prepare_bulk(
        stage_actions,
        Action,
        prototype,
        (
            "name",
            "type",
            "script",
            "script_type",
            "state_available",
            "state_unavailable",
            "state_on_success",
            "state_on_fail",
            "multi_state_available",
            "multi_state_unavailable",
            "multi_state_on_success_set",
            "multi_state_on_success_unset",
            "multi_state_on_fail_set",
            "multi_state_on_fail_unset",
            "params",
            "log_files",
            "hostcomponentmap",
            "display_name",
            "description",
            "ui_options",
            "allow_to_terminate",
            "partial_execution",
            "host_action",
            "venv",
            "allow_in_maintenance_mode",
        ),
    )
    Action.objects.bulk_create(actions)


def copy_stage_sub_actions(bundle):
    sub_actions = []
    for ssubaction in StageSubAction.objects.all():
        if ssubaction.action.prototype.type == "component":
            parent = Prototype.objects.get(
                bundle=bundle,
                type="service",
                name=ssubaction.action.prototype.parent.name,
            )
        else:
            parent = None

        action = Action.objects.get(
            prototype__bundle=bundle,
            prototype__type=ssubaction.action.prototype.type,
            prototype__name=ssubaction.action.prototype.name,
            prototype__parent=parent,
            prototype__version=ssubaction.action.prototype.version,
            name=ssubaction.action.name,
        )
        sub = copy_obj(
            ssubaction,
            SubAction,
            (
                "name",
                "display_name",
                "script",
                "script_type",
                "state_on_fail",
                "multi_state_on_fail_set",
                "multi_state_on_fail_unset",
                "params",
            ),
        )
        sub.action = action
        sub_actions.append(sub)

    SubAction.objects.bulk_create(sub_actions)


def copy_stage_component(stage_components, stage_proto, prototype, bundle):
    components = []
    for c in stage_components:
        comp = copy_obj(
            c,
            Prototype,
            (
                "type",
                "path",
                "name",
                "version",
                "required",
                "monitoring",
                "bound_to",
                "constraint",
                "requires",
                "display_name",
                "description",
                "adcm_min_version",
                "config_group_customization",
                "venv",
            ),
        )
        comp.bundle = bundle
        comp.parent = prototype
        components.append(comp)

    Prototype.objects.bulk_create(components)
    for sp in StagePrototype.objects.filter(type="component", parent=stage_proto):
        proto = Prototype.objects.get(name=sp.name, type="component", parent=prototype, bundle=bundle)
        copy_stage_actions(StageAction.objects.filter(prototype=sp), proto)
        copy_stage_config(StagePrototypeConfig.objects.filter(prototype=sp), proto)


def copy_stage_import(stage_imports, prototype):
    imports = prepare_bulk(
        stage_imports,
        PrototypeImport,
        prototype,
        (
            "name",
            "min_version",
            "max_version",
            "min_strict",
            "max_strict",
            "default",
            "required",
            "multibind",
        ),
    )
    PrototypeImport.objects.bulk_create(imports)


def copy_stage_config(stage_config, prototype):
    target_config = []
    for sc in stage_config:
        obj_copy = copy_obj(
            sc,
            PrototypeConfig,
            (
                "name",
                "subname",
                "default",
                "type",
                "description",
                "display_name",
                "limits",
                "required",
                "ui_options",
                "group_customization",
            ),
        )
        if sc.action:
            obj_copy.action = Action.objects.get(prototype=prototype, name=sc.action.name)

        obj_copy.prototype = prototype
        target_config.append(obj_copy)

    PrototypeConfig.objects.bulk_create(target_config)


def check_license(proto):
    return Prototype.objects.filter(license_hash=proto.license_hash, license="accepted").exists()


def copy_stage(bundle_hash, bundle_proto):
    bundle = copy_obj(
        bundle_proto,
        Bundle,
        ("name", "version", "edition", "description"),
    )
    bundle.hash = bundle_hash
    try:
        bundle.save()
    except IntegrityError:
        shutil.rmtree(settings.BUNDLE_DIR / bundle.hash)
        err("BUNDLE_ERROR", f'Bundle "{bundle_proto.name}" {bundle_proto.version} already installed')

    stage_prototypes = StagePrototype.objects.exclude(type="component")
    copy_stage_prototype(stage_prototypes, bundle)

    for sp in stage_prototypes:
        proto = Prototype.objects.get(name=sp.name, type=sp.type, bundle=bundle)
        copy_stage_actions(StageAction.objects.filter(prototype=sp), proto)
        copy_stage_config(StagePrototypeConfig.objects.filter(prototype=sp), proto)
        copy_stage_component(
            StagePrototype.objects.filter(parent=sp, type="component"),
            sp,
            proto,
            bundle,
        )

        for se in StagePrototypeExport.objects.filter(prototype=sp):
            pe = PrototypeExport(prototype=proto, name=se.name)
            pe.save()

        copy_stage_import(StagePrototypeImport.objects.filter(prototype=sp), proto)

    copy_stage_sub_actions(bundle)
    copy_stage_upgrade(StageUpgrade.objects.all(), bundle)

    return bundle


def update_bundle_from_stage(
    bundle,
):  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    for sp in StagePrototype.objects.all():
        try:
            prototype = Prototype.objects.get(bundle=bundle, type=sp.type, name=sp.name, version=sp.version)
            prototype.path = sp.path
            prototype.version = sp.version
            prototype.description = sp.description
            prototype.display_name = sp.display_name
            prototype.required = sp.required
            prototype.shared = sp.shared
            prototype.monitoring = sp.monitoring
            prototype.adcm_min_version = sp.adcm_min_version
            prototype.venv = sp.venv
            prototype.config_group_customization = sp.config_group_customization
            prototype.allow_maintenance_mode = sp.allow_maintenance_mode
        except Prototype.DoesNotExist:
            prototype = copy_obj(
                sp,
                Prototype,
                (
                    "type",
                    "path",
                    "name",
                    "version",
                    "required",
                    "shared",
                    "monitoring",
                    "bound_to",
                    "constraint",
                    "requires",
                    "display_name",
                    "description",
                    "adcm_min_version",
                    "venv",
                    "config_group_customization",
                    "allow_maintenance_mode",
                ),
            )
            prototype.bundle = bundle

        prototype.save()
        for saction in StageAction.objects.filter(prototype=sp):
            try:
                action = Action.objects.get(prototype=prototype, name=saction.name)
                update_obj(
                    action,
                    saction,
                    (
                        "type",
                        "script",
                        "script_type",
                        "state_available",
                        "state_on_success",
                        "state_on_fail",
                        "multi_state_available",
                        "multi_state_on_success_set",
                        "multi_state_on_success_unset",
                        "multi_state_on_fail_set",
                        "multi_state_on_fail_unset",
                        "params",
                        "log_files",
                        "hostcomponentmap",
                        "display_name",
                        "description",
                        "ui_options",
                        "allow_to_terminate",
                        "partial_execution",
                        "host_action",
                        "venv",
                        "allow_in_maintenance_mode",
                    ),
                )
            except Action.DoesNotExist:
                action = copy_obj(
                    saction,
                    Action,
                    (
                        "name",
                        "type",
                        "script",
                        "script_type",
                        "state_available",
                        "state_on_success",
                        "state_on_fail",
                        "multi_state_available",
                        "multi_state_on_success_set",
                        "multi_state_on_success_unset",
                        "multi_state_on_fail_set",
                        "multi_state_on_fail_unset",
                        "params",
                        "log_files",
                        "hostcomponentmap",
                        "display_name",
                        "description",
                        "ui_options",
                        "allow_to_terminate",
                        "partial_execution",
                        "host_action",
                        "venv",
                        "allow_in_maintenance_mode",
                    ),
                )
                action.prototype = prototype

            action.save()

            SubAction.objects.filter(action=action).delete()
            for ssubaction in StageSubAction.objects.filter(action=saction):
                sub = copy_obj(
                    ssubaction,
                    SubAction,
                    (
                        "script",
                        "script_type",
                        "state_on_fail",
                        "multi_state_on_fail_set",
                        "multi_state_on_fail_unset",
                        "params",
                    ),
                )
                sub.action = action
                sub.save()

        for sc in StagePrototypeConfig.objects.filter(prototype=sp):
            flist = (
                "default",
                "type",
                "description",
                "display_name",
                "limits",
                "required",
                "ui_options",
                "group_customization",
            )
            act = None
            if sc.action:
                act = Action.objects.get(prototype=prototype, name=sc.action.name)

            try:
                pconfig = PrototypeConfig.objects.get(prototype=prototype, action=act, name=sc.name, subname=sc.subname)
                update_obj(pconfig, sc, flist)
            except PrototypeConfig.DoesNotExist:
                pconfig = copy_obj(sc, PrototypeConfig, ("name", "subname") + flist)
                pconfig.action = act
                pconfig.prototype = prototype

            pconfig.save()

        PrototypeExport.objects.filter(prototype=prototype).delete()
        for se in StagePrototypeExport.objects.filter(prototype=sp):
            pe = PrototypeExport(prototype=prototype, name=se.name)
            pe.save()

        PrototypeImport.objects.filter(prototype=prototype).delete()
        for si in StagePrototypeImport.objects.filter(prototype=sp):
            pi = copy_obj(
                si,
                PrototypeImport,
                (
                    "name",
                    "min_version",
                    "max_version",
                    "min_strict",
                    "max_strict",
                    "default",
                    "required",
                    "multibind",
                ),
            )
            pi.prototype = prototype
            pi.save()

    Upgrade.objects.filter(bundle=bundle).delete()
    for su in StageUpgrade.objects.all():
        upg = copy_obj(
            su,
            Upgrade,
            (
                "name",
                "description",
                "min_version",
                "max_version",
                "min_strict",
                "max_strict",
                "state_available",
                "state_on_success",
                "from_edition",
            ),
        )
        upg.bundle = bundle
        upg.save()


def clear_stage():
    for model in STAGE:
        model.objects.all().delete()


def delete_bundle(bundle):
    providers = HostProvider.objects.filter(prototype__bundle=bundle)
    if providers:
        provider = providers[0]
        err(
            "BUNDLE_CONFLICT",
            f'There is provider #{provider.id} "{provider.name}" of bundle '
            f'#{bundle.id} "{bundle.name}" {bundle.version}',
        )

    clusters = Cluster.objects.filter(prototype__bundle=bundle)
    if clusters:
        cluster = clusters[0]
        err(
            "BUNDLE_CONFLICT",
            f'There is cluster #{cluster.id} "{cluster.name}" of bundle #{bundle.id} "{bundle.name}" {bundle.version}',
        )

    adcm = ADCM.objects.filter(prototype__bundle=bundle)
    if adcm:
        err("BUNDLE_CONFLICT", f'There is adcm object of bundle #{bundle.id} "{bundle.name}" {bundle.version}')

    if bundle.hash != "adcm":
        try:
            shutil.rmtree(Path(settings.BUNDLE_DIR, bundle.hash))
        except FileNotFoundError:
            logger.info(
                "Bundle %s %s was removed in file system. Delete bundle in database",
                bundle.name,
                bundle.version,
            )

    bundle_id = bundle.id
    bundle.delete()

    for role in Role.objects.filter(class_name="ParentRole"):
        if not role.child.all():
            role.delete()

    ProductCategory.re_collect()
    cm.status_api.post_event("delete", "bundle", bundle_id)


def check_services():
    s = {}
    for prototype in StagePrototype.objects.filter(type="service"):
        if prototype.name in s:
            msg = "There are more than one service with name {}"
            err("BUNDLE_ERROR", msg.format(prototype.name))

        s[prototype.name] = prototype.version


def check_adcm_version(bundle):
    if not bundle.adcm_min_version:
        return

    if rpm.compare_versions(bundle.adcm_min_version, settings.ADCM_VERSION) > 0:
        msg = "This bundle required ADCM version equal to {} or newer."
        err("BUNDLE_VERSION_ERROR", msg.format(bundle.adcm_min_version))


def get_stage_bundle(bundle_file):
    bundle = None
    clusters = StagePrototype.objects.filter(type="cluster")
    providers = StagePrototype.objects.filter(type="provider")

    if clusters:
        if len(clusters) > 1:
            err(
                "BUNDLE_ERROR",
                f'There are more than one ({len(clusters)}) cluster definition in bundle "{bundle_file}"',
            )

        if providers:
            err(
                "BUNDLE_ERROR",
                f'There are {len(providers)} host provider definition in cluster type bundle "{bundle_file}"',
            )

        hosts = StagePrototype.objects.filter(type="host")
        if hosts:
            err(
                "BUNDLE_ERROR",
                f'There are {len(hosts)} host definition in cluster type bundle "{bundle_file}"',
            )

        check_services()
        bundle = clusters[0]
    elif providers:
        if len(providers) > 1:
            err(
                "BUNDLE_ERROR",
                f'There are more than one ({len(providers)}) host provider definition in bundle "{bundle_file}"',
            )

        services = StagePrototype.objects.filter(type="service")
        if services:
            err(
                "BUNDLE_ERROR",
                f'There are {len(services)} service definition in host provider type bundle "{bundle_file}"',
            )

        hosts = StagePrototype.objects.filter(type="host")
        if not hosts:
            err(
                "BUNDLE_ERROR",
                f'There isn\'t any host definition in host provider type bundle "{bundle_file}"',
            )

        bundle = providers[0]
    else:
        err(
            "BUNDLE_ERROR",
            f'There isn\'t any cluster or host provider definition in bundle "{bundle_file}"',
        )

    check_adcm_version(bundle)

    return bundle
