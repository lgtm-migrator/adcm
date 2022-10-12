from dataclasses import dataclass, asdict
from pprint import pformat

import allure
import pytest
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import wait_until_step_succeeds

from tests.ui_tests.app.helpers.configs_generator import prepare_group_config, generate_group_configs, TYPES
from tests.ui_tests.app.page.service.page import ServiceConfigPage
from tests.ui_tests.conftest import login_over_api
from tests.ui_tests.test_cluster_list_page import (
    check_default_field_values_in_configs,
    prepare_cluster_and_open_config_page,
)


@allure.step("Check save button and save config")
def _check_save_in_configs(cluster_config_page, field_type, expected_state, is_default):
    """
    Check save button and save config.
    It is a workaround for each type of field because it won't work other way on ui with selenium.
    """

    config_row = cluster_config_page.config.get_config_row(field_type)
    if field_type == 'list':
        cluster_config_page.config.click_add_item_btn_in_row(config_row)
    if field_type in ['string', 'integer', 'text', 'float', 'file', 'json']:
        config_row.click()
    if field_type == 'secrettext':
        cluster_config_page.config.reset_to_default(config_row)
    if field_type == 'boolean' and is_default:
        for _ in range(3):
            cluster_config_page.config.click_boolean_checkbox(config_row)
    if field_type == 'password':
        if is_default:
            cluster_config_page.config.reset_to_default(config_row)
        else:
            config_row.click()
    if field_type == 'map':
        cluster_config_page.config.click_add_item_btn_in_row(config_row)
        cluster_config_page.config.reset_to_default(config_row)
    cluster_config_page.config.check_save_btn_state_and_save_conf(expected_state)


@dataclass()
class ParamCombination:
    field_type: str
    activatable: bool
    active: bool
    group_advanced: bool
    default: bool
    required: bool
    read_only: bool
    field_invisible: bool
    field_advanced: bool


def prepare_combinations():
    return [
        ParamCombination(
            field_type, group_advanced, is_default, is_required, is_read_only, activatable, active, invisible, advanced
        )
        for field_type in TYPES
        for group_advanced in (True, False)
        for is_default in (True, False)
        for is_required in (True, False)
        for is_read_only in (True, False)
        for activatable in (True, False)
        for active in (True, False)
        for invisible in (True, False)
        for advanced in (True, False)
    ]

@pytest.fixture()
def clean(sdk_client_ms):
    yield
    sdk_client_ms.cluster().delete()


@pytest.mark.full()
@pytest.mark.parametrize("combo", prepare_combinations())
@pytest.mark.usefixtures("clean")  # pylint: disable-next=too-many-locals
def test_group_configs_fields_invisible_false_222(combo: ParamCombination, adcm_credentials, sdk_client_ms: ADCMClient, app_ms):
    """Test group configs with not-invisible fields"""
    login_over_api(app_ms, adcm_credentials).wait_config_loaded()
    config, expected, path = prepare_group_config(generate_group_configs(group_invisible=False, **asdict(combo)))
    _, page = prepare_cluster_and_open_config_page(sdk_client_ms, path, app_ms)

    if combo.group_advanced:
        page.config.check_no_rows_or_groups_on_page()
    else:
        check_expectations(
            page=page,
            is_group_activatable=combo.activatable,
            is_invisible=combo.field_invisible,
            is_advanced=combo.field_advanced,
            is_default=combo.default,
            is_read_only=combo.read_only,
            field_type=combo.field_type,
            alerts_expected=expected['alerts'],
            config=config,
        )
    page.config.click_on_advanced()
    check_expectations(
        page=page,
        is_group_activatable=combo.activatable,
        is_invisible=combo.field_invisible,
        is_advanced=combo.field_advanced,
        is_default=combo.default,
        is_read_only=combo.read_only,
        field_type=combo.field_type,
        alerts_expected=expected['alerts'],
        config=config,
    )
    if (not combo.read_only) and (not combo.field_invisible) and (not combo.required) and combo.default:
        _check_save_in_configs(page, combo.field_type, expected["save"], combo.default)


# alerts_expected = expected['alerts']
def check_expectations(
    page, is_group_activatable, is_invisible, is_advanced, is_default, is_read_only, field_type, alerts_expected, config
):
    """lololo"""
    with allure.step('Check that group field is visible'):
        group_name = page.config.get_group_names()[0].text
        assert group_name == 'group', "Group with name 'group' should be visible"

    # why ?
    if not is_group_activatable:
        return

    if not page.config.advanced:
        page.config.check_group_is_active(group_name, config['config'][0]['active'])

    # rewrite this condition, it's unreadable
    if not (not is_invisible and ((page.config.advanced and is_advanced) or not is_advanced)):
        with allure.step("Check field is invisible"):
            assert len(page.config.get_all_config_rows()) == 1, "Field should not be visible"
            return

    page.config.expand_or_close_group(group_name, expand=True)

    def _check_field_is_visible_after_group_is_epanded():
        assert len(page.config.get_all_config_rows()) >= 2, "Field should be visible"

    wait_until_step_succeeds(_check_field_is_visible_after_group_is_epanded, timeout=5, period=0.2)

    config_item = page.config.get_all_config_rows()[1]

    if is_default:
        check_default_field_values_in_configs(page, config_item, field_type, config)

    if is_read_only and config_item.tag_name == 'app-field':
        assert page.config.is_element_read_only(config_item), f"Config field {field_type} should be read only"

    if alerts_expected and not is_read_only:
        if field_type == "map":
            is_advanced = page.config.advanced
            page.driver.refresh()
            if is_advanced:
                page.config.click_on_advanced()
            page.config.expand_or_close_group(group_name, expand=True)
        if field_type == "password":
            page.config.reset_to_default(config_item)
        else:
            page.config.click_on_advanced()
            page.config.click_on_advanced()
        page.config.check_invalid_value_message(field_type)
