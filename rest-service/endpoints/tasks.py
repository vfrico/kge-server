#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding:utf-8
#
# endpoints/falcon.py: Falcon file to manage tasks resources
# Copyright (C) 2016  Víctor Fernández Rico <vfrico@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json
import copy
import falcon
import kgeserver.server as server

# Import parent directory (data_access)
import sys
sys.path.insert(0, '..')
try:
    import data_access
    import async_server.tasks as async_tasks
    import async_server.celery as celery_server
except ImportError:
    raise


class TasksResource():

    def on_get(self, req, resp, task_id):
        """Return one task"""
        tdao = data_access.TaskDAO()

        task_obj, err = tdao.get_task_by_id(task_id)
        if task_obj is None:
            raise falcon.HTTPNotFound(description=str(err))

        t_uuid = celery_server.app.AsyncResult(task_obj['celery_uuid'])

        task = {}
        task["state"] = t_uuid.state
        # task["is_ready"] = t_uuid.ready()
        task["id"] = task_obj["id"]

        try:
            if req.get_param_as_bool('get_debug_info'):
                task["debug"] = task_obj
        except Exception:
            pass

        if t_uuid.state == "SUCCESS":
            # Look if exists some next
            if "next" in task_obj and task_obj["next"] is not None:
                print("This task has next {}".format(task_obj["next"]))
                try:
                    if req.get_param_as_bool('no_redirect'):
                        resp.status = falcon.HTTP_200
                    else:
                        resp.status = falcon.HTTP_303
                except Exception:
                    resp.status = falcon.HTTP_303
                resp.location = task_obj["next"]

        elif t_uuid.state == "STARTED":
            # Get task progress and show to the user
            celery_uuid = "celery-task-progress-" + task_obj['celery_uuid']

            redis = data_access.RedisBackend()
            task_progress = redis.get(celery_uuid)

            try:
                if "progress" in task_progress:
                    task["progress"] = task_progress["progress"]
            except TypeError:
                pass

            resp.status = falcon.HTTP_200

        elif t_uuid.state == "FAILURE":
            task["error"] = {"exception": str(t_uuid.result),
                             "traceback": t_uuid.traceback}

        response = {"task": task}
        resp.body = json.dumps(response)
        resp.content_type = 'application/json'
