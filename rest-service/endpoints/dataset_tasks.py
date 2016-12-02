#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding:utf-8
#
# dataset_tasks.py: Falcon file to manage resources which creates tasks
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
except ImportError:
    raise


class GenerateTriplesResource():

    def on_post(self, req, resp, dataset_id):
        """Generates a task to insert triples on dataset. Async petition.

        Reads from body the parameters such as SPARQL queries

        {"generate_triples":
            {
                "graph_pattern": "<SPARQL Query (Where part)>",
                "levels": 2,
                "batch_size": 30000   # Optional
            }
        }

        :param id dataset_id: The dataset to insert triples into
        """
        try:
            extra = "Couldn't decode the input stream (body)."
            body = json.loads(req.stream.read().decode('utf-8'))

            if "generate_triples" not in body:
                extra = ("It was expected a JSON object with a "
                         "'generate_triples' param")
                raise KeyError
            json_rpc = body['generate_triples']
            if "levels" not in json_rpc:
                extra = ("The 'generate_triples' JSON object must contain"
                         "level attribute")
                raise KeyError
        except (json.decoder.JSONDecodeError, KeyError,
                ValueError, TypeError) as err:
            msg = ("Couldn't read body correctly from HTTP request. "
                   "Please, read the documentation carefully and try again. "
                   "Extra info: " + extra)
            resp.body = json.dumps({"status": 400, "message": msg})
            resp.content_type = 'application/json'
            resp.status = falcon.HTTP_400
            return

        dataset_dao = data_access.DatasetDAO()
        dataset_dto, err = dataset_dao.get_dataset_by_id(dataset_id)
        if dataset_dto is None:
            raise falcon.HTTPNotFound(description=str(err))

        if dataset_dto.status != 0:
            raise falcon.HTTPConflict(
                title="The dataset is not in a correct state",
                description=("The dataset {id} has an status {status}, which "
                             "is not valid to insert triples. Required is 0 "
                             ).format(**dataset_dto.to_dict()))

        # Generate the filepath to the dataset
        # dtset_path = dataset_dto.get_binary_dataset()

        # Read arguments from body
        graph_pattern = json_rpc.pop("graph_pattern")
        levels = json_rpc.pop("levels")
        try:
            batch_size = json_rpc.pop("batch_size")
        except KeyError:
            batch_size = None

        # Launch async task
        task = async_tasks.generate_dataset_from_sparql.delay(
            dataset_id, graph_pattern, levels, batch_size=batch_size)

        # Create a new task
        task_dao = data_access.TaskDAO()
        task_obj, err = task_dao.add_task_by_uuid(task.id)
        if task_obj is None:
            raise falcon.HTTPNotFound(description=str(err))
        task_obj["next"] = "/datasets/" + dataset_id
        task_dao.update_task(task_obj)

        msg = "Task {} created successfuly".format(task_obj['id'])
        textbody = {"status": 202, "message": msg}
        resp.location = "/tasks/" + str(task_obj['id'])
        resp.body = json.dumps(textbody)
        resp.content_type = 'application/json'
        resp.status = falcon.HTTP_202


class DatasetIndex():
    # TODO: Save anywhere the number of trees used

    def on_post(self, req, resp, dataset_id):
        """Generates a search index to perform data lookups operations.

        This task may take long time to complete, so it uses tasks.

        :query int n_trees: The number of trees generated
        """
        dataset_dao = data_access.DatasetDAO()
        dataset_dto, err = dataset_dao.get_dataset_by_id(dataset_id)
        if dataset_dto is None:
            raise falcon.HTTPNotFound(description=str(err))

        # Check actual status of the dataset
        if not dataset_dto.is_trained():
            dataset_status = dataset_dto.status
            err_title = "The dataset is not in correct state"
            msg = "The dataset has {} status and is not ready to be indexed"
            raise falcon.HTTPConflict(title=err_title,
                                      description=msg.format(dataset_status))

        # Dig for the param on Query Params
        n_trees = req.get_param_as_int('n_trees')

        # Call to the task
        task = async_tasks.build_search_index.delay(dataset_id, n_trees)

        # Create the new task
        task_dao = data_access.TaskDAO()
        task_obj, err = task_dao.add_task_by_uuid(task.id)
        if task_obj is None:
            raise falcon.HTTPNotFound(description=str(err))
        task_obj["next"] = "/datasets/" + dataset_id
        task_dao.update_task(task_obj)

        msg = "Task {} created successfuly".format(task_obj['id'])
        textbody = {"status": 202, "message": msg}
        resp.location = "/tasks/" + str(task_obj['id'])
        resp.body = json.dumps(textbody)
        resp.content_type = 'application/json'
        resp.status = falcon.HTTP_202


class DatasetTrain():
    # TODO: Test if works well

    def on_post(self, req, resp, dataset_id):
        """Generates a model that fits the dataset and trains it

        It usually takes several hours for big datasets

        This changes the dataset status from 0 to 1 once finished. To indicate
        dataset cannot be modified, this parameter will be set to a negative
        value.

        :query int algorithm_id: The algorithm used to train the dataset
        """
        dataset_dao = data_access.DatasetDAO()
        dataset_dto, err = dataset_dao.get_dataset_by_id(dataset_id)
        if dataset_dto is None:
            raise falcon.HTTPNotFound(description=str(err))

        force_train = req.get_param_as_bool("force_train")

        # Check if dataset can be trained
        if not dataset_dto.is_untrained() and not force_train:
            dataset_status = dataset_dto.status
            err_title = "The dataset is not in correct state"
            msg = "The dataset has {} status and is not ready to be trained"
            raise falcon.HTTPConflict(title=err_title,
                                      description=msg.format(dataset_status))

        # Dig for the limit param on Query Params
        algorithm_id = req.get_param('algorithm_id', required=True)

        # Obtain the algorithm
        algorithm_dao = data_access.AlgorithmDAO()
        algorithm, err = algorithm_dao.get_algorithm_by_id(algorithm_id)
        if algorithm is None:
            raise falcon.HTTPNotFound(message=str(err))

        # If it all goes ok, add id of algorithm to db
        dataset_dao.set_algorithm(dataset_id, algorithm_id)
        dataset_dao.set_status(dataset_id, -1)

        # Launch async task
        task = async_tasks.train_dataset_from_algorithm.delay(
            dataset_id, algorithm)

        # Create the new task
        task_dao = data_access.TaskDAO()
        task_obj, err = task_dao.add_task_by_uuid(task.id)
        if task_obj is None:
            raise falcon.HTTPNotFound(description=str(err))
        task_obj["next"] = "/datasets/" + dataset_id
        task_dao.update_task(task_obj)

        msg = "Task {} created successfuly".format(task_obj['id'])
        textbody = {"status": 202, "message": msg}
        resp.location = "/tasks/" + str(task_obj['id'])
        resp.body = json.dumps(textbody)
        resp.content_type = 'application/json'
        resp.status = falcon.HTTP_202
