#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding:utf-8
#
# data_access.py: Contains several DAO for different objects on the service
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
import os
import time
import sqlite3
import redis
import json
import kgeserver.server as server
import kgeserver.dataset as dataset
import kgeserver.wikidata_dataset as wikidata_dataset
import data_access.dataset_dao as dataset_dao
import data_access.algorithm_dao as algorithm_dao
import data_access.data_access_base as data_access_base
DatasetDAO = dataset_dao.DatasetDAO
AlgorithmDAO = algorithm_dao.AlgorithmDAO
MainDAO = data_access_base.MainDAO


class RedisBackend:
    """Creates a wrapper for redis to manage dicts inside Redis

    Reads Redis configuration from environment variables. These variables
    are intended to be created with docker.
        * REDIS_PORT_6379_TCP_ADDR
        * REDIS_PORT_6379_TCP_PORT
    """
    def __init__(self):
        # Reads REDIS conf from environment variables
        port = os.environ['REDIS_PORT_6379_TCP_PORT']
        host = os.environ['REDIS_PORT_6379_TCP_ADDR']

        self.connection = redis.StrictRedis(host=host, port=port, db=0)

    def get(self, key):
        task_str = self.connection.get(key)
        if task_str is None:
            return None
        else:
            return json.loads(task_str.decode("utf-8"))

    def set(self, key, value):
        task_str = json.dumps(value)
        return self.connection.set(key, task_str.encode("utf-8"))

    def incr(self, key):
        return self.connection.incr(key)


class TaskDAO():
    """Manages the Task resource from Redis KeyStore database.

    To keep the number of tasks that exists on redis, a key named tasks will
    be created. It will only contain an integer to be incremented with every
    task created.
    """
    def __init__(self, backend=RedisBackend()):
        self.task = {"celery_uuid": None,
                     "id": None,
                     "next": None}

        self.redis = backend

    def redis_id(self):
        return self.redis_id_build(self.task["id"])

    def redis_id_build(self, id):
        return "task:{}".format(id)

    def get_task_by_id(self, task_id):
        return self.redis.get(self.redis_id_build(task_id)), None

    def add_task_by_uuid(self, task_uuid):
        self.task["id"] = self.redis.incr("tasks")
        self.task["celery_uuid"] = task_uuid
        self.redis.set(self.redis_id(), self.task)
        return self.task, None

    def update_task(self, task):
        self.redis.set(self.redis_id_build(task["id"]), task)


class ProgressDTO():
    """DTO object to help manage progress between python and the database
    """
    def __init__(self):
        self.current = None
        self.total = None
        self.current_steps = None
        self.total_steps = None

    def fill_from_dict(self, dictionary):
        """Given a dict, fills the ProgressDTO

        :param dict dictionary: The dict to fill DTO from
        """
        self.current = dictionary["current"]
        self.total = dictionary["total"]
        self.current_steps = dictionary["current_steps"]
        self.total_steps = dictionary["total_steps"]

    def to_dict(self):
        """Create a dict from params on the DTO

        :returns: A dictionary with all params on DTO
        :rtype: dict
        """
        return {"total": self.total,
                "current": self.current,
                "total_steps": self.total_steps,
                "current_steps": self.current_steps}


class ProgressDAO():
    """This class allows to manage the status of a task on the database
    """
    def __init__(self, backend=RedisBackend()):
        self.redis = backend

    def _redis_id(self, celery_uuid):
        """auxiliar method to fastly create the redis id
        """
        return "celery-task-progress-{}".format(celery_uuid)

    def set_progress(self, celery_uuid, progress_dto):
        """Set the full progress on redis from ProgressDTO

        :param ProgressDTO progress_dto: The progress object
        :param str celery_uuid: The uuid of the task
        """
        progress = {"progress": progress_dto.to_dict()}
        return self.redis.set(self._redis_id(celery_uuid), progress)

    def get_progress(self, celery_uuid):
        """Get a DTO of the progress given a celery task UUID

        :param str celery_uuid: The uuid of the task
        :return: The progress of the celery task
        :rtype: ProgressDTO
        """
        progress = self.redis.get(self._redis_id(celery_uuid))
        p_dto = ProgressDTO()
        p_dto.fill_from_dict(progress["progress"])
        return p_dto

    def update_progress(self, celery_uuid, current):
        """Changes only current progres of an existing task

        :param str celery_uuid: The uuid of the task
        :param int current: The current progress to save
        """
        progress = self.get_progress(celery_uuid)
        progress.current = current
        return self.set_progress(celery_uuid, progress)

    def create_progress(self, celery_uuid, total):
        """Creates a progress DTO (empty) on the database

        :param str celery_uuid: The uuid of the task
        :param int total: Give a total value of the progress of the task
        """
        progress = ProgressDTO()
        progress.total = total
        return self.set_progress(celery_uuid, progress)
