#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding:utf-8
#
# routes.py: Falcon file to serve API routes
# Copyright (C) 2016 - 2017  Víctor Fernández Rico <vfrico@gmail.com>
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
from falcon_cors import CORS
import data_access
import kgeserver.server as server
import async_server.tasks as async_tasks
import async_server.celery as celery_server
import logging

from endpoints.datasets import (DatasetFactory,
                                DatasetResource,
                                EmbeddingResource,
                                TriplesResource)
from endpoints.dataset_tasks import (GenerateTriplesResource,
                                     DatasetIndex,
                                     DatasetTrain)
from endpoints.dataset_prediction import (PredictSimilarEntitiesResource,
                                          DistanceTriples)
from endpoints.algorithms import AlgorithmFactory, AlgorithmResource
from endpoints.tasks import TasksResource

# CORS
cors = CORS(allow_all_origins=True, allow_all_headers=True,
            allow_all_methods=True, expose_headers_list=['*'])

# falcon.API instances are callable WSGI apps
app = falcon.API(middleware=[cors.middleware])

# Resources are represented by long-lived class instances
dataset = DatasetResource()
datasetcreate = DatasetFactory()
similar_entities = PredictSimilarEntitiesResource()
triples = TriplesResource()
gentriples = GenerateTriplesResource()
triples_distance = DistanceTriples()
dataset_train = DatasetTrain()
dataset_index = DatasetIndex()
dataset_embedding = EmbeddingResource()

task_resource = TasksResource()

algorithm_resource = AlgorithmResource()
algorithm_factory = AlgorithmFactory()

# All API routes and the object that will handle each one
app.add_route('/datasets/', datasetcreate)
app.add_route('/datasets/{dataset_id}', dataset)
app.add_route('/datasets/{dataset_id}/triples', triples)
app.add_route('/datasets/{dataset_id}/generate_triples', gentriples)
app.add_route('/datasets/{dataset_id}/distance', triples_distance)
app.add_route('/datasets/{dataset_id}/similar_entities/{entity}',
              similar_entities)
app.add_route('/datasets/{dataset_id}/similar_entities', similar_entities)
app.add_route('/datasets/{dataset_id}/train', dataset_train)
app.add_route('/datasets/{dataset_id}/generate_index', dataset_index)
app.add_route('/datasets/{dataset_id}/embeddings', dataset_embedding)


app.add_route('/tasks/{task_id}', task_resource)

app.add_route('/algorithms/{algorithm_id}', algorithm_resource)
app.add_route('/algorithms/', algorithm_factory)
