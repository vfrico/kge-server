#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding:utf-8
#
# tasks.py: Contains several async tasks to be executed with Celery
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

from __future__ import absolute_import, unicode_literals
from .celery import app
import time
import json
import skge
import kgeserver.dataset as dataset
import kgeserver.algorithm as algorithm
import kgeserver.server as server

# Import parent directory (data_access)
import sys
sys.path.insert(0, '..')
try:
    import data_access
except ImportError:
    pass


@app.task(bind=True)
def generate_dataset_from_sparql(self, dataset_path, graph_pattern, levels,
                                 **keyw_args):
    """Creates a recurrent dataset from a seed vector

    This method is intended to be called only with celery *.delay()*, to
    be executed in foreground. The status of the generation can be queried
    through it's celery UUID.

    :param levels: The number of levels to scan
    :param dataset_path: The path to dataset file
    :param graph_pattern: The main query containing triples
    :kwparam limit_ent: Use only for testing purposes
    """
    from celery import current_task  # in task definition
    # Load current dataset
    dtset = dataset.Dataset()
    dtset.load_from_binary(dataset_path)

    # Obtains the Redis connection from celery.
    redis = self.app.backend
    # The id of the object
    celery_uuid = "celery-task-progress-"+self.request.id
    # Saves the empty id to be retrieved first time without error
    redis.set(celery_uuid, "{}".encode("utf-8"))

    # Get the seed vector and load first entities
    seed_vector = dtset.load_from_graph_pattern(where=graph_pattern)

    def status_callback(status):
        """Saves the progress of the task on redis db"""
        # Create progress object
        progress = {"current": status['it_analyzed'],
                    "total": status['it_total'],
                    "current_steps": status['round_curr']+1,
                    "total_steps": status['round_total']
                    }

        # Retrieve task from redis
        task = redis.get(celery_uuid).decode("utf-8")
        task = json.loads(task)

        # Add task progress
        task['progress'] = progress

        # Save again on redis
        task = json.dumps(task).encode("utf-8")
        redis.set(celery_uuid, task)
        return

    # Build the optional args dict
    keyw_args["ext_callback"] = status_callback

    # Call to the *heavy* method
    dtset.load_dataset_recurrently(levels, seed_vector, **keyw_args)

    # Save new binary
    dtset.save_to_binary(dataset_path)

    return False


@app.task(bind=True)
def train_dataset_from_algorithm(self, dataset_id, algorithm_dict):
    """Trains a dataset given an algorithm

    It is able to save the progress of training.
    :param str dataset_path: The path where binary dataset is located
    :param dict algorithm: An algorithm to be used in dataset training
    """

    dataset_dao = data_access.DatasetDAO()
    dataset_dto, err = dataset_dao.get_dataset_by_id(dataset_id)
    # Generate the filepath to the dataset
    dtset_path = dataset_dao.build_dataset_path()
    # Loads the current dataset
    dtset = dataset.Dataset()
    dtset.load_from_binary(dtset_path)

    # Creates an optional parameters dict for better readability
    kwargs = {
        'train_all': True,  # All dataset will be trained, not validated
        'test_all': -1,  # No validation is going to be performed
        'model_type': skge.TransE,  # The default model will be used
        'ncomp': algorithm_dict['embedding_size'],  # Provided by the algorithm
        'margin': algorithm_dict['margin'],  # Provided by the algorithm
        'max_epochs': algorithm_dict['max_epochs'],  # Max number of iterations
    }

    # Heavy task
    model = algorithm.ModelTrainer(dtset, **kwargs)
    modeloentrenado = model.run()
    model_path = dtset_path[:-4] + "_model.bin"
    modeloentrenado.save(model_path)

    # Update values on DB when model training has finished
    dataset_dao.set_status(dataset_id, 1)
    dataset_dao.set_model(dataset_id, model_path)

    return False


@app.task(bind=True)
def insert_triples_from_graph_pattern(self, dataset_path, graph_pattern):
    # Loads the current dataset
    dtset = dataset.Dataset()
    dtset.load_from_binary(dataset_path)

    # Heavy task
    dtset.load_from_graph_pattern(verbose=2, where=graph_pattern)
    # dt.show()
    dtset.save_to_binary(dataset_path)

    # TODO Update values on dataset db

    return False


@app.task(bind=True)
def build_search_index(self, dataset_id, n_trees):
    """Builds the search index and stores in disk

    :param str model_path: The path to the binary file which stores the model
    :param int n_trees: The number of trees to be generated. Default is 100
    """
    # Check input Params
    if n_trees is None:
        n_trees = 100

    # Creates the progress object in redis
    celery_uuid = self.request.id
    progres_dao = data_access.ProgressDAO()
    progres_dao.create_progress(celery_uuid, 3)
    progres_dao.update_progress(celery_uuid, 0)

    dataset_dao = data_access.DatasetDAO()
    # Set working status
    dataset_dao.set_status(dataset_id, -2)
    model_path, err = dataset_dao.get_model(dataset_id)
    # Load the model and initialize the search index
    model = skge.TransE.load(model_path)
    search_index = server.SearchIndex()

    # File to store the search index
    search_index_file = model_path[:-4] + "_annoy_{}.bin".format(n_trees)

    # Execute heavy task and track the progress
    progres_dao.update_progress(celery_uuid, 1)
    search_index.build_from_trained_model(model, n_trees)
    progres_dao.update_progress(celery_uuid, 2)
    search_index.save_to_binary(search_index_file)
    progres_dao.update_progress(celery_uuid, 3)

    # Update values on DB
    dataset_dao.set_status(dataset_id, 2)
    dataset_dao.set_search_index(dataset_id, search_index_file)

    return False


def find_embeddings_on_model(dataset_id, entities):
    """Returns a list with the corresponding embeddings

    This will return a list like this:

    [["Q1", [0, 1, -1, 0.4]], ["Q5", [1, -0.5, -0.1, 0]]]

    :param str model_path: The path to the binary model
    :param list entities: A list with the URI (or identifiers) of entities
    :returns: The embedding vector of each entity
    :rtype: dict
    """
    # Expected to return: {entities: [], embeddings: []} IN THE SAME ORDER!!
    dataset_dao = data_access.DatasetDAO()
    # dataset, err = dataset_dao.get_dataset_by_id(dataset_id)
    # if dataset is None:
    #     raise LookupError("The dataset couldn't be located")

    dataset_path, err = dataset_dao.get_binary_path(dataset_id)
    if dataset_path is None:
        raise FileNotFoundError("The binary dataset doesn't exist on database")

    # Load dataset from binary
    dtset = dataset.Dataset()
    dtset.load_from_binary(dataset_path)

    model_path, err = dataset_dao.get_model(dataset_id)
    if model_path is None:
        raise FileNotFoundError("The model path does not exist on database")
    # Load the model and initialize the search index
    model = skge.TransE.load(model_path)

    return_list = []
    for entity in entities:
        position = dtset.get_entity_id(entity)
        if position < 0:
            continue
        else:
            embedding = model.E[position]
        return_list.append([entity, embedding.tolist()])
    return return_list
