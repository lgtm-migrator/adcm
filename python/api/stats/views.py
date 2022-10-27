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

from guardian.mixins import PermissionListMixin
from rest_framework import permissions
from rest_framework.response import Response

from api.base_view import GenericUIView
from cm import config
from cm.models import JobLog, TaskLog


class JobStats(PermissionListMixin, GenericUIView):
    queryset = JobLog.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    permission_required = ['cm.view_joblog']

    def get(self, request, pk):
        """
        Show jobs stats
        """
        jobs = self.get_queryset().filter(id__gt=pk)
        data = {
            config.Job.FAILED: jobs.filter(status=config.Job.FAILED).count(),
            config.Job.SUCCESS: jobs.filter(status=config.Job.SUCCESS).count(),
            config.Job.RUNNING: jobs.filter(status=config.Job.RUNNING).count(),
        }
        return Response(data)


class TaskStats(PermissionListMixin, GenericUIView):
    queryset = TaskLog.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    permission_required = ['cm.view_tasklog']

    def get(self, request, pk):
        """
        Show tasks stats
        """
        tasks = self.get_queryset().filter(id__gt=pk)
        data = {
            config.Job.FAILED: tasks.filter(status=config.Job.FAILED).count(),
            config.Job.SUCCESS: tasks.filter(status=config.Job.SUCCESS).count(),
            config.Job.RUNNING: tasks.filter(status=config.Job.RUNNING).count(),
        }
        return Response(data)
