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
def generate_dataset_from_sparql(dataset_path, levels, seed_vector_query):
    """Ejecuta la operación de generar un dataset de forma recurrente

    Ejecuta también la operación de obtener el vector de inicio
    """
    print("Ejecutando tarea")

    # Load dataset
    dtset = dataset.Dataset()
    dtset.load_from_binary(dataset_path)

    if seed_vector_query:
        seed_vector = dtset.get_seed_vector(where=seed_vector_query)
    else:
        seed_vector = dtset.get_seed_vector()

    dtset.load_dataset_recurrently(levels, seed_vector, limit_ent=100)
    print("Carga finalizada")
    dtset.save_to_binary(dataset_path)
    print("Guardo dataset")

    return False
