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

from adcm.tests.base import BaseTestCase
from cm.models import ConcernCause, ConcernItem, ConcernType, MessageTemplate
from cm.tests.utils import gen_concern_item, generate_hierarchy


class ADCMEntityConcernTest(BaseTestCase):
    """Tests for `cm.models.ADCMEntity` lock-related methods"""

    def setUp(self):
        self.hierarchy = generate_hierarchy()

    def test_is_locked__false(self):
        for obj in self.hierarchy.values():
            self.assertFalse(obj.locked)

            for item in obj.concerns.all():
                self.assertFalse(item, "No locks expected")

    def test_is_locked__true(self):
        lock = gen_concern_item(ConcernType.Lock)
        for obj in self.hierarchy.values():
            obj.add_to_concerns(lock)

            self.assertTrue(obj.locked)

    def test_is_locked__deleted(self):
        lock = gen_concern_item(ConcernType.Lock)
        for obj in self.hierarchy.values():
            obj.add_to_concerns(lock)

        lock.delete()
        for obj in self.hierarchy.values():
            self.assertFalse(obj.locked)

    def test_add_to_concern__none(self):
        lock = None
        for obj in self.hierarchy.values():
            obj.add_to_concerns(lock)

            self.assertFalse(obj.locked)

    def test_add_to_concern__deleted(self):
        lock = ConcernItem(type=ConcernType.Lock, name=None, reason="unsaved")
        for obj in self.hierarchy.values():
            obj.add_to_concerns(lock)

            self.assertFalse(obj.locked)

    def test_add_to_concern(self):
        lock = gen_concern_item(ConcernType.Lock)
        for obj in self.hierarchy.values():
            obj.add_to_concerns(lock)

            self.assertTrue(obj.locked)

            locks = obj.concerns.all()

            self.assertEqual(len(locks), 1)
            self.assertEqual(locks[0].pk, lock.pk)

    def test_remove_from_concern__none(self):
        nolock = None
        lock = gen_concern_item(ConcernType.Lock)
        for obj in self.hierarchy.values():
            obj.add_to_concerns(lock)
            obj.remove_from_concerns(nolock)

            self.assertTrue(obj.locked)

    def test_remove_from_concern__deleted(self):
        nolock = ConcernItem(type=ConcernType.Lock, name=None, reason="unsaved")
        lock = gen_concern_item(ConcernType.Lock)
        for obj in self.hierarchy.values():
            obj.add_to_concerns(lock)
            obj.remove_from_concerns(nolock)

            self.assertTrue(obj.locked)

    def test_get_own_issue__empty(self):
        cluster = self.hierarchy["cluster"]

        self.assertIsNone(cluster.get_own_issue(ConcernCause.Config))

    def test_get_own_issue__others(self):
        cluster = self.hierarchy["cluster"]
        service = self.hierarchy["service"]
        reason = MessageTemplate.get_message_from_template(MessageTemplate.KnownNames.ConfigIssue.value, source=cluster)
        issue_type = ConcernCause.Config
        issue = ConcernItem.objects.create(type=ConcernType.Issue, reason=reason, owner=cluster, cause=issue_type)
        cluster.add_to_concerns(issue)
        service.add_to_concerns(issue)

        self.assertIsNone(service.get_own_issue(issue_type))

    def test_get_own_issue__exists(self):
        cluster = self.hierarchy["cluster"]
        reason = MessageTemplate.get_message_from_template(MessageTemplate.KnownNames.ConfigIssue.value, source=cluster)
        issue_type = ConcernCause.Config
        issue = ConcernItem.objects.create(type=ConcernType.Issue, reason=reason, owner=cluster, cause=issue_type)
        cluster.add_to_concerns(issue)

        self.assertIsNotNone(cluster.get_own_issue(issue_type))
