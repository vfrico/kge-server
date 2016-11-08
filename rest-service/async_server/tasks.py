from __future__ import absolute_import, unicode_literals
from .celery import app
import time
import json
import skge
import kgeserver.dataset as dataset
import kgeserver.algorithm as algorithm


@app.task(bind=True)
def generate_dataset_from_sparql(self, dataset_path, levels, **keyw_args):
    """Creates a recurrent dataset from a seed vector

    This method is intended to be called only with celery *.delay()*, to
    be executed in foreground. The status of the generation can be queried
    through it's celery UUID.

    :param levels: The number of levels to scan
    :param dataset_path: The path to dataset file
    :param sparql_seed_query: A sparql chunk to start quering
    :param graph_pattern: A sparql chunk to perform the entity lookup
    :param limit_ent: Use only for testing purposes
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

    # Get the seed vector
    if "sparql_seed_query" in keyw_args:
        # If user provides arguments for seed_vector_query, use them
        whereseed = keyw_args.pop("sparql_seed_query")
        seed_vector = dtset.get_seed_vector(where=whereseed)
    else:
        seed_vector = dtset.get_seed_vector()

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
def train_dataset_from_algorithm(self, dataset_path, algorithm_dict):
    """Trains a dataset given an algorithm

    It is able to save the progress of training.
    :param str dataset_path: The path where binary dataset is located
    :param dict algorithm: An algorithm to be used in dataset training
    """

    # Loads the current dataset
    dtset = dataset.Dataset()
    dtset.load_from_binary(dataset_path)

    # Creates an optional parameters dict for better readability
    kwargs = {
        'train_all': True,  # All dataset will be trained, not validated
        'test_all': -1,  # No validation is going to be performed
        'model_type': skge.TransE,  # The default model will be used
        'ncomp': algorithm_dict['embedding_size'],  # Provided by the algorithm
        'margin': algorithm_dict['margin'],  # Provided by the algorithm
    }

    # Heavy task
    model = algorithm.ModelTrainer(dtset, **kwargs)
    modeloentrenado = model.run()
    modeloentrenado.save(dataset_path+".model.bin")

    return False
