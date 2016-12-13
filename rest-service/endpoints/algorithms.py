#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding:utf-8
#
# algorithms.py: Falcon file to manage algorithm resources
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


class AlgorithmResource():

    def on_get(self, req, resp, algorithm_id):
        """Shows the representation of the selected algorithm

        :param int algorithm_id: The id of the algorithm
        """
        algorithm_dao = data_access.AlgorithmDAO()

        algorithm, err = algorithm_dao.get_algorithm_by_id(algorithm_id)
        if algorithm is None:
            raise falcon.HTTPNotFound(message=str(err))

        resp.body = json.dumps(algorithm)
        resp.content_type = 'application/json'
        resp.status = falcon.HTTP_200


class AlgorithmFactory():

    def on_get(self, req, resp):
        """Shows the representation of all algorithms available
        """
        algorithm_dao = data_access.AlgorithmDAO()

        algorithms, err = algorithm_dao.get_all_algorithms()
        if algorithms is None:
            raise falcon.HTTPNotFound(message=str(err))

        resp.body = json.dumps(algorithms)
        resp.content_type = 'application/json'
        resp.status = falcon.HTTP_200

    def on_post(self, req, resp):
        """Insert algorithm on the service

        :param dict algorithm: The algorithm to be inserted
        """
        # Read body
        try:
            extra = "Couldn't decode the input stream (body)."
            body = json.loads(req.stream.read().decode('utf-8'))

            if "algorithm" not in body:
                raise falcon.HTTPMissingParam("algorithm")

            # Redefine variables
            user_algorithm = body["algorithm"]

        except (json.decoder.JSONDecodeError, KeyError,
                ValueError, TypeError) as err:
            print(err)
            err_title = "HTTP Body request not loaded correctly"
            msg = ("The body couldn't be correctly loaded from HTTP request. "
                   "Please, read the documentation carefully and try again. "
                   "Extra info: " + extra)
            raise falcon.HTTPBadRequest(title=err_title, description=msg)

        algorithm_dao = data_access.AlgorithmDAO()
        algorithm_id, err = algorithm_dao.insert_algorithm(user_algorithm)
        if algorithm_id is None:
            raise falcon.HTTPBadRequest(title="Missing algorithm param",
                                        description=str(err))

        msg = "Algorithm {} created successfuly".format(algorithm_id)
        textbody = {"status": 202, "message": msg}
        resp.body = json.dumps(textbody)
        resource_path = "/algorithm/{}".format(algorithm_id)
        resp.location = resource_path
        resp.status = falcon.HTTP_201
