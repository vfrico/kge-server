from __future__ import absolute_import, unicode_literals
from .celery import app
import time
import json
import kgeserver.dataset as dataset


@app.task
def add(x, y):
    time.sleep(10)
    return x + y


@app.task
def mul(x, y):
    return x * y


@app.task
def xsum(numbers):
    return sum(numbers)


@app.task(bind=True)
def generate_dataset_from_sparql(self, dataset_path, levels, **keyw_args):
    """Ejecuta la operación de generar un dataset de forma recurrente

    Ejecuta también la operación de obtener el vector de inicio
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

    # If user provides arguments for seed_vector_query, use them
    if "sparql_seed_query" in keyw_args:
        whereseed = keyw_args.pop("sparql_seed_query")
        seed_vector = dtset.get_seed_vector(where=whereseed)
    else:
        seed_vector = dtset.get_seed_vector()

    # WIP: Worker should save the status anywhere to inform the REST USER API
    def status_callback(status):
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
