#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding:utf-8
#
# common_hooks.py: Helper functions to read body requests
# Copyright (C) 2016 - 2017 Víctor Fernández Rico <vfrico@gmail.com>
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
import falcon

# Import parent directory (data_access)
import sys
sys.path.insert(0, '..')
try:
    import data_access
except ImportError:
    raise


def read_body_as_json(req):
    """Reads the request body and returns a dict with the content

    If body is empty, returns a void python dictionary

    :return: A dictionary or similar python object (list)
    :rtype: Object
    """
    try:
        body_req = req.stream.read().decode('utf-8')
        if body_req is None or body_req == "":
            return {}
        else:
            return json.loads(body_req)

    except (json.decoder.JSONDecodeError) as err:
        msg = ("Please, read the documentation carefully and try again. "
               "Couldn't decode the input stream (body).")
        raise falcon.HTTPBadRequest(
            title="Couldn't read body correctly from HTTP request",
            description=str(msg))


def check_dataset_exsistence(req, resp, resource, params):
    """Will check if input dataset exists.

    :returns: A dataset DTO
    """
    dataset_dao = data_access.DatasetDAO()
    cache = req.get_param_as_bool("use_cache", blank_as_true=True)
    params["dataset_dto"], err = dataset_dao.get_dataset_by_id(
        params['dataset_id'], use_cache=cache)
    if params["dataset_dto"] is None:
        raise falcon.HTTPNotFound(
                title="Dataset {} not found".format(params['dataset_id']),
                description="The dataset does not exists. " + str(err))


def dataset_untrained_status(req, resp, resource, params):
    """Raises an error if dataset is not on an untrained state
    Must be executed after check_dataset_exsistence. This will not inform
    about dataset existence, instead will return an undefined error.

    If query param ignore_status is true, it will not raise any error
    """
    status, dataset_dto = _get_dataset_status(params['dataset_id'])
    ignore_status = req.get_param_as_bool("ignore_status")
    if status != 0 and not ignore_status:
        raise falcon.HTTPConflict(
            title="The dataset is not in a correct state",
            description=("The dataset {id} has an status {status}, which "
                         "is not valid to insert triples. Required is 0 "
                         ).format(**dataset_dto.to_dict()))


def dataset_trained_status(req, resp, resource, params):
    """Raises an error if dataset is not on an trained state
    Must be executed after check_dataset_exsistence. This will not inform
    about dataset existence, instead will return an undefined error.

    If query param ignore_status is true, it will not raise any error
    """
    status, dataset_dto = _get_dataset_status(params['dataset_id'])
    ignore_status = req.get_param_as_bool("ignore_status")
    if status != 1 and not ignore_status:
        raise falcon.HTTPConflict(
            title="The dataset is not in a correct state",
            description=("The dataset {id} has an status {status}, which "
                         "is not valid to generate an index. Required is 1 "
                         ).format(**dataset_dto.to_dict()))


def _get_dataset_status(dataset_id):
    """Returns the dataset status

    :rtype: integer
    """
    d_dao = data_access.DatasetDAO()
    d_dto, err = d_dao.get_dataset_by_id(dataset_id, use_cache=True)
    return d_dto.status, d_dto
