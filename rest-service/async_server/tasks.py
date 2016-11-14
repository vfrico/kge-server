from __future__ import absolute_import, unicode_literals
from .celery import app
import time
import json
import skge
import kgeserver.dataset as dataset
import kgeserver.algorithm as algorithm

# Import parent directory (data_access)
import sys
sys.path.insert(0, '..')
import data_access


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

    dataset_dao = data_access.DatasetDAO()
    # Set working status
    dataset_dao.set_status(dataset_id, -2)
    model_path = dataset_dao.get_model(dataset_id)
    # Load the model and initialize the search index
    model = skge.TransE.load(model_path)
    search_index = server.SearchIndex()

    # File to store the search index
    search_index_file = model_path[:-4] + str("_annoy_{}.bin".format(n_trees))

    # Heavy task
    search_index.build_from_trained_model(model, n_trees)
    search_index.save_to_binary(search_index_file)

    # Update values on DB
    dataset_dao.set_status(dataset_id, 2)
    dataset_dao.set_search_index(dataset_id, search_index_file)

    return False
