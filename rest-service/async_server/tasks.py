from __future__ import absolute_import, unicode_literals
from .celery import app
import time
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


@app.task
def generate_dataset_from_sparql(dataset_path, levels, seed_vector_query,
                                 entity_query, **keyw_args):
    """Ejecuta la operación de generar un dataset de forma recurrente

    Ejecuta también la operación de obtener el vector de inicio
    """
    # Load current dataset
    dtset = dataset.Dataset()
    dtset.load_from_binary(dataset_path)

    # If user provides arguments for seed_vector_query, use them
    if seed_vector_query:
        seed_vector = dtset.get_seed_vector(where=seed_vector_query)
    else:
        seed_vector = dtset.get_seed_vector()

    # WIP: Worker should save the status anywhere to inform the REST USER API
    def status_callback(status):
        # TODO: This will analyze the status variable to track progress
        return

    # Build the optional args dict
    new_kwargs = {}
    new_kwargs["ext_callback"] = status_callback
    if "limit_ent" in keyw_args:
        new_kwargs["limit_ent"] = keyw_args["limit_ent"]

    # Call to the *heavy* method
    dtset.load_dataset_recurrently(levels, seed_vector, **new_kwargs)

    # Save new binary
    dtset.save_to_binary(dataset_path)

    return False
