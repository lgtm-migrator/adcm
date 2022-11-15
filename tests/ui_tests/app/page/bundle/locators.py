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

"""Bundle page locators"""

from selenium.webdriver.common.by import By
from tests.ui_tests.app.helpers.locator import Locator
from tests.ui_tests.app.page.common.common_locators import ObjectPageLocators


class BundleLocators:
    """Bundle main page elements locators"""

    class MenuNavigation:
        """Bundle main menu navigation elements locators"""

        main = Locator(By.CSS_SELECTOR, "a[adcm_test='tab_main']", "Main link in side menu")


class BundleMainMenuLocators(ObjectPageLocators):
    """Bundle object page main menu locators"""

    text = Locator(By.CSS_SELECTOR, "mat-card-content", "Bundle main page text")
