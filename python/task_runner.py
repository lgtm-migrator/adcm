#!/usr/bin/env python3
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

# pylint: disable=unused-import, useless-return, protected-access, bare-except, global-statement

import os
import signal
import subprocess
import sys
import time

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

import adcm.init_django  # pylint: disable=unused-import
from cm.job import finish_task, re_prepare_job
from cm.logger import logger
from cm.models import JobLog, JobStatus, LogStorage, TaskLog

TASK_ID = 0


def terminate_job(task, jobs):
    running_job = jobs.get(status=JobStatus.RUNNING)

    if running_job.pid:
        os.kill(running_job.pid, signal.SIGTERM)
        finish_task(task, running_job, JobStatus.ABORTED)
    else:
        finish_task(task, None, JobStatus.ABORTED)


def terminate_task(signum, frame):
    logger.info("cancel task #%s, signal: #%s", TASK_ID, signum)
    task = TaskLog.objects.get(id=TASK_ID)
    jobs = JobLog.objects.filter(task_id=TASK_ID)

    i = 0
    while i < 10:
        if jobs.filter(status=JobStatus.RUNNING):
            terminate_job(task, jobs)
            break
        i += 1
        time.sleep(0.5)

    if i == 10:
        logger.warning("no jobs running for task #%s", TASK_ID)
        finish_task(task, None, JobStatus.ABORTED)

    os._exit(signum)


signal.signal(signal.SIGTERM, terminate_task)


def run_job(task_id, job_id, err_file):
    logger.debug("task run job #%s of task #%s", job_id, task_id)
    cmd = [
        "/adcm/python/job_venv_wrapper.sh",
        TaskLog.objects.get(id=task_id).action.venv,
        str(settings.CODE_DIR / "job_runner.py"),
        str(job_id),
    ]
    logger.info("task run job cmd: %s", " ".join(cmd))
    try:
        proc = subprocess.Popen(cmd, stderr=err_file)
        res = proc.wait()

        return res
    except Exception:  # pylint: disable=broad-except
        logger.error("exception running job %s", job_id)

        return 1


def set_log_body(job):
    name = job.sub_action.script_type if job.sub_action else job.action.script_type
    log_storage = LogStorage.objects.filter(job=job, name=name, type__in=["stdout", "stderr"])
    for ls in log_storage:
        file_path = settings.RUN_DIR / f"{ls.job.id}" / f"{ls.name}-{ls.type}.{ls.format}"
        with open(file_path, "r", encoding=settings.ENCODING_UTF_8) as f:
            body = f.read()

        LogStorage.objects.filter(job=job, name=ls.name, type=ls.type).update(body=body)


def run_task(task_id, args=None):
    logger.debug("task_runner.py called as: %s", sys.argv)
    try:
        task = TaskLog.objects.get(id=task_id)
    except ObjectDoesNotExist:
        logger.error("no task %s", task_id)

        return

    task.pid = os.getpid()
    task.save()
    jobs = JobLog.objects.filter(task_id=task.id).order_by("id")
    if not jobs:
        logger.error("no jobs for task %s", task.id)
        finish_task(task, None, JobStatus.FAILED)

        return

    err_file = open(settings.LOG_DIR / "job_runner.err", "a+", encoding=settings.ENCODING_UTF_8)

    logger.info("run task #%s", task_id)

    job = None
    count = 0
    res = 0
    for job in jobs:
        if args == "restart" and job.status == JobStatus.SUCCESS:
            logger.info('skip job #%s status "%s" of task #%s', job.id, job.status, task_id)

            continue
        task.refresh_from_db()
        re_prepare_job(task, job)
        job.start_date = timezone.now()
        job.save()
        res = run_job(task.id, job.id, err_file)
        set_log_body(job)

        # For multi jobs task object state and/or config can be changed by adcm plugins
        if task.task_object is not None:
            try:
                task.task_object.refresh_from_db()
            except ObjectDoesNotExist:
                task.object_id = 0
                task.object_type = None

        count += 1
        if res != 0:
            break

    if res == 0:
        finish_task(task, job, JobStatus.SUCCESS)
    else:
        finish_task(task, job, JobStatus.FAILED)

    err_file.close()

    logger.info("finish task #%s, ret %s", task_id, res)


def do():
    global TASK_ID
    if len(sys.argv) < 2:
        print(f"\nUsage:\n{os.path.basename(sys.argv[0])} task_id [restart]\n")
        sys.exit(4)
    elif len(sys.argv) > 2:
        TASK_ID = sys.argv[1]
        run_task(sys.argv[1], sys.argv[2])
    else:
        TASK_ID = sys.argv[1]
        run_task(sys.argv[1])


if __name__ == "__main__":
    do()
