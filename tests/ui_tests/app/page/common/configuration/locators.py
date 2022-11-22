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

"""Configuration page locators"""

from selenium.webdriver.common.by import By
from tests.ui_tests.app.helpers.locator import Locator, TemplateLocator


class CommonConfigMenu:
    """Configuration menu locators"""

    group_btn = TemplateLocator(By.XPATH, "//mat-expansion-panel-header[.//span[text()='{}']]", 'Group "{}" button')
    group_row = TemplateLocator(By.XPATH, "//mat-expansion-panel[.//span[text()='{}']]", 'Group "{}" row')

    advanced_label = Locator(By.XPATH, "//mat-checkbox[.//span[text()='Advanced']]", "Advanced label")
    search_input = Locator(By.CSS_SELECTOR, "#config_search_input", "Search input")
    search_input_clear_btn = Locator(
        By.CSS_SELECTOR, "app-search button[aria-label='Clear']", "Clear search input button"
    )
    description_input = Locator(
        By.CSS_SELECTOR,
        "input[data-placeholder='Description configuration']",
        "Config description input",
    )
    save_btn = Locator(By.XPATH, "//button[.//span[text()='Save']]", "Save configuration button")
    history_btn = Locator(By.XPATH, "//button[.//mat-icon[text()='history']]", "History button")

    compare_version_select = Locator(By.CSS_SELECTOR, "mat-select[placeholder='History']", "Base version to compare")
    compare_to_select = Locator(By.CSS_SELECTOR, "mat-select[placeholder='Compare to']", "Compare to version select")
    config_version_option = TemplateLocator(
        By.XPATH, "//mat-option//span[contains(text(), '{}')]", "Config version with text: {}"
    )
    # use it to check config diff existence by finding text entry
    config_diff = TemplateLocator(
        By.XPATH,
        "//app-field[.//div[@adcm_test='{}']]//mat-list-item//span[contains(text(), '{}')]",
        'Config diff of option "{}" with "{}" in text',
    )
    config_row = Locator(By.CSS_SELECTOR, "app-config-fields>*", "Configuration row")
    text_row = Locator(By.TAG_NAME, "app-fields-textbox", "Configuration textbox row")
    field_error = TemplateLocator(By.XPATH, "//mat-error[contains(text(), '{}')]", 'Error "{}"')
    info_tooltip_icon = TemplateLocator(
        By.XPATH,
        "//div[contains(@adcm_test, '{}')]//mat-icon[@mattooltipclass='info-tooltip']",
        'info tooltip "{}"',
    )
    tooltip_text = Locator(By.CSS_SELECTOR, "mat-tooltip-component div", "Tooltip text")
    loading_text = Locator(By.XPATH, "//span[text()='Loading...']", "Loading text")

    class ConfigRow:
        """Configuration menu configuration row locators"""

        name = Locator(By.CSS_SELECTOR, "label:not(.mat-checkbox-layout)", "Row name")
        value = Locator(By.CSS_SELECTOR, "input:not([type='checkbox']),textarea", "Row value")

        input = Locator(
            By.CSS_SELECTOR,
            '*:not([style="display: none;"])>mat-form-field input,textarea',
            "Row input",
        )
        password = Locator(
            By.XPATH,
            "(.//app-fields-password/div[not(contains(@style, 'none'))]//input)[1]",
            "Password input",
        )
        confirm_password = Locator(
            By.XPATH,
            "(.//app-fields-password/div[not(contains(@style, 'none'))]//input)[2]",
            "Confirm password input",
        )
        history = Locator(By.CSS_SELECTOR, "mat-list-item span.accent", "Row history")
        reset_btn = Locator(By.CSS_SELECTOR, "button[mattooltip='Reset to default']", "Reset button")
        group_chbx = Locator(By.CSS_SELECTOR, ".group-checkbox mat-checkbox", "Group checkbox")
        checkbox = Locator(By.CSS_SELECTOR, "app-fields-boolean mat-checkbox", "Checkbox")

        # complex parameters
        add_item_btn = Locator(
            By.XPATH,
            ".//button//mat-icon[text()='add_circle_outline']",
            "Add item to parameter button",
        )
        map_item = Locator(By.CSS_SELECTOR, "div.item", "Map parameter item")
        map_input_key = Locator(By.XPATH, ".//input[@formcontrolname='key']", "Map input key input")
        map_input_value = Locator(By.XPATH, ".//input[@formcontrolname='value']", "Map input value input")

        select_btn = Locator(By.CSS_SELECTOR, "app-fields-dropdown", "Select option button")
        select_item = Locator(By.CSS_SELECTOR, ".mat-select-panel mat-option", "Select option item")

    class ConfigGroup:
        """Configuration menu configuration group locators"""

        name = Locator(By.CSS_SELECTOR, "mat-panel-title>span", "Group name")
        expansion_btn = Locator(By.CSS_SELECTOR, "mat-expansion-panel-header", "Expansion button")
        item_row = Locator(By.CSS_SELECTOR, "app-field", "Item in group")

    class HistoryRow:
        """Configuration menu history row locators"""

        history_select = Locator(By.CSS_SELECTOR, "mat-select[placeholder='History']", "History select")
        compare_select = Locator(By.CSS_SELECTOR, "mat-select[placeholder='Compare to']", "Compare select")
        option = Locator(By.CSS_SELECTOR, "mat-option", "Option in select")
