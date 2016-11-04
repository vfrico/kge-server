.. _restservice:


REST Service
============
.. Esto es una definición de primer nivel y tenemos que definir un buen diseño.
.. Partes de este servicio pueden quedar fuera del prácticum para continuar a
.. partir del TFG. Primero centrarnos en la parte servidor de
.. predicciones (para poder hacer pruebas). Por orden de prioridad.

    Server: Debería ofrecer los métodos para buscar entidades similares
    tanto por id, por uri, como por vector de embedding.

    Dataset: Creación de datasets desde un método a partir de un SPARQL
    endpoint y una query semilla o un path a un fichero Ntriples.
    El servicio debería crear un id único para el dataset para poder
    pasárselo al algoritmo de training.

    Algorithm: Encontrar el mejor modelo dado un dataset y
    rangos de parámetros.
    /algorithm/1
    Crear con petición asíncrona.
    POST /algorithm?dataset={id}&param1= &param2= etc...

El servicio REST está compuesto principalmente de un recurso dataset con
distintas operaciones

Endpoints
---------
Aquí se detallarán todos los endpoints del servicio. El valor de la prioridad
que se muestra indica la importancia que se le va a dar a la implementación
de ese servicio. Cuanto menor sea, más importancia se le dará.

Gestión de Datasets
```````````````````

Un dataset se compone de los siguientes campos públicos:

{"entities", "relations", "triples", "status", "algorithm"}

El recurso *Algorithm*, que todavía no está disponible, dispondrá de todos
los parámetros que se han utilizado para entrenar el dataset. Por el momento
sólo contendrá "embedding_size".

El dataset irá mudando de *status* dependiendo de si sólo contiene datos,
si ha sido también entrenado, o si ya está listo para predecir tripletas.

.. http:get:: /datasets/(int:dataset_id)/

    Obtener toda la información de un dataset.

    **Ejemplo**

    :http:get:`/datasets/1/`

    .. sourcecode:: json

        {
            "dataset": {
                "entities": 664444,
                "relations": 647,
                "id": 1,
                "status": 2,
                "triples": 3261785,
                "algorithm": 100
            }
        }

    :param int dataset_id: id único del dataset
    :statuscode 200: Devuelve el dataset sin errores
    :statuscode 404: El dataset no ha sido encontrado

.. ver celery para añadir peticiones asíncronas a un "demonio" https://github.com/celery/celery/
.. http:put:: /datasets/(int:dataset_id)/train?algorithm=(int:id_algorithm)

    Entrenar un dataset con un algoritmo dado. Se usará un modelo de petición
    asíncrona, dado que puede tardar una cantidad de tiempo considerable.

    El dataset ya tiene que existir y no debe haber sido entrenado previamente

    Se pondrá la petición en una cola y se devolverá un 202 ACCPEPTED, con
    la cabecera LOCATION: rellena con una tarea (/task/{id}), que mostrará el progreso.
    Al finalizar, la tarea mostrará un 303, ya que se habrá creado un nuevo
    recurso /datasets/{id}, y la cabecera LOCATION vendrá rellena con esa URI.

    Basado en: <http://restcookbook.com/Resources/asynchroneous-operations/>

    :prioridad: 2
    :param int dataset_id: id único del dataset.
    :query int id_algorithm: id del algoritmo utilizado para entrenar el dataset.

.. http:get:: /datasets/

    Obtener todos los ID de Datasets. No muestra (por defecto) los tamaños
    de los datasets.

    :statuscode 200: All the datasets are shown correctly


.. http:get:: /dataset_types

    Obtener todos los tipos de dataset disponibles en el sistema. No pueden
    ser modificados.

    :prioridad: 1
    :statuscode 200: Se muestran adecuadamente los tipos


.. Problema: Un WikidataDataset no tiene las mismas operaciones que un Dataset
.. normal. Ver cómo puede afectar esto en la gestión de los métodos HTTP:
.. **Solución**: Utilizar sólo los métodos *públicos* de Dataset
.. http:post:: /dataset?type=(int:dataset_type)

    Crear un dataset nuevo y vacío. Se deberán utilizar otras consultas para
    llenar con tripletas el dataset. Se creará el objeto con un determinado
    *dataset_type*, que determinará qué funciones podrá tener en un futuro.

    :prioridad: 1
    :query int dataset_type: El tipo de dataset a ser creado.
    :statuscode 201: Se ha creado un dataset nuevo correctamente. Ver cabecera
                     Location para saber la URI del recurso.
    :statuscode 404: El *dataset_type* no existe.
    :statuscode 500: No se ha podido crear el dataset.


.. http:post:: /datasets/(int:dataset_id)/triples

    Añadir una tripleta al dataset. Se debe enviar un JSON con un objeto o lista
    de objetos *triple*, que tienen los parámetros.
    {"subject", "predicate", "object"}¹. Sólo se pueden añadir tripletas a un
    dataset con estado *0*, ya que no puede ser reentrenado.

    ¹:*También se suelen representar las tripletas con la notación de head,*
    *label y tail, refiriéndose respectivamente a subject, predicate y object*

    **Ejemplo**

    :http:post:`/datasets/6/triples`

    .. sourcecode:: json

        {"triples": [
            {"subject":"Q1492", "predicate":"P17", "object":"Q29"},
            {"subject":"Q2807", "predicate":"P17", "object":"Q29"}
                    ]
        }

    :param int dataset_id: id único del dataset.
    :statuscode 202: La petición se ha procesado correctamente.
    :statuscode 404: El *dataset_id* no existe.
    :statuscode 409: El estado del *dataset_id* no es correcto.


.. http:post:: /datasets/(int:dataset_id)/generate_triples

    Adds triples to dataset doing a sequence of SPARQL queries by levels,
    starting with a seed vector. This operation is supported only by
    certain types of datasets.

    The request will use asyncronous operations. This means that the request
    will not be satisfied on the same HTTP connection. Instead, the service
    will return a `task` resource that will be queried with the progress
    of the task.

    .. sourcecode:: json

        {
        "generate_triples":
            {
                "levels": 2,
                "sparql_seed_query": "",
                "sparql_graph_pattern": "",
                "limit_ent": 200,
            }
        }

    :param int dataset_id: id único del dataset.
    :statuscode 404: El *dataset_id* no existe.
    :statuscode 409: The *dataset_id* does not allow this operation
    :statuscode 202: Se ha creado una tarea. Ver /tareas para más información


Tareas
``````

Esta factoría almacena toda la información que generen todas las peticiones
asíncronas en el servidor

.. http:get:: /tasks/(int:task_id)

    Muestra la progresión de la tarea con id *task_id*. Las tareas que hayan
    acabado pueden ser eliminadas sin previo aviso.

    Some tasks can inform to the user about its progress. It is done through
    the progress param, which has *do* and *total* arguments. The *do* shows
    the tasks done at the moment of the request, and the *total* shows all the
    tasks planned to do.

    :param int task_id: id único de la tarea a consultar
    :statuscode 200: Muestra el estado de la tarea
    :statuscode 303: La tarea se ha completado. See Location para ver
                     el recurso al que afecta.
    :statuscode 404: La *task_id* no existe.


.. http:delete:: /tasks/(int:task_id)

    Elimina una tarea de la base de datos. Sólo se eliminarán aquellas tareas
    que no se estén ejecutando. No será posible consultar el progreso en el
    futuro, pero se mantendrá el resultado que haya producido dicha tarea.

    :prioridad: 1
    :statuscode 204: The task has been deleted
    :statuscode 404: The task does not exists and cannot be deleted
    :statuscode 409: The current state of the task does not allow to delete it

Predicción de tripletas
```````````````````````

.. http:get:: /datasets/(int:dataset_id)/similar_entities/(string:entity)?limit=(int:limit)?search_k=(int:search_k)

    Obtener las *limit* entidades más similares a *entity* dentro
    del *dataset_id*. El número dado en *limit* excluye la propia entidad.
    Sólo es válido para ciertas representaciones de entidad.


    **Ejemplo**

    :http:get:`/datasets/1/similar_entities/Q1492?limit=1`

    .. sourcecode:: json

        {    "similar_entities":
            {    "response":
                [
                    {"distance": 0, "entity": "http://www.wikidata.org/entity/Q1492"},
                    {"distance": 0.8224636912345886, "entity": "http://www.wikidata.org/entity/Q15090"}
                ],
                "entity": "http://www.wikidata.org/entity/Q1492",
                "limit": 2
            },
            "dataset": {
                "entities": 664444,
                "relations": 647,
                "id": 1,
                "status": 2,
                "triples": 3261785,
                "algorithm": 100
            }
        }


    :param int dataset_id: id único del dataset
    :param string entity: Representación de la entidad (Elemento o vector)
    :query int limit: Límite de entidades similares que se piden. Por defecto
                      tiene el valor 10.
    :query int search_k: Número máximo de nodos donde se realiza la búsqueda.
                         Mejora la calidad de las búsquedas, a costa de un
                         rendimiento más bajo. Por defecto tiene el valor -1.


.. http:post:: /datasets/(int:dataset_id)/similar_entities?limit=(int:limit)?search_k=(int:search_k)

    Obtener las *limit* entidades más similares a *entity* dentro
    del *dataset_id*. El número dado en *limit* excluye la propia entidad.
    La representación de la entidad puede ser una URI completa o cualquier
    otra de su representación

    Debe de incluirse en el body un documento JSON formateado así:

    **Ejemplo**

    :http:post:`/datasets/0/similar_entities?limit=1`

    .. sourcecode:: json

        { "entity":
              {"value": "http://www.wikidata.org/entity/Q1492", "type": "uri"}
        }

    *Respuesta*

    .. sourcecode:: json

        {    "similar_entities":
            {    "response":
                [
                    {"distance": 0, "entity": "http://www.wikidata.org/entity/Q1492"},
                    {"distance": 0.8224636912345886, "entity": "http://www.wikidata.org/entity/Q15090"}
                ],
                "entity": "http://www.wikidata.org/entity/Q1492",
                "limit": 2
            },
            "dataset": {
                "entities": 664444,
                "relations": 647,
                "id": 1,
                "status": 2,
                "triples": 3261785,
                "algorithm": 100
            }
        }


    :param int dataset_id: id único del dataset
    :param string entity: Representación de la entidad (Elemento o vector)
    :query int limit: Límite de entidades similares que se piden. Por defecto
                      tiene el valor 10.
    :query int search_k: Número máximo de nodos donde se realiza la búsqueda.
                         Mejora la calidad de las búsquedas, a costa de un
                         rendimiento más bajo. Por defecto tiene el valor -1.


.. http:get:: /datasets/(int:dataset_id)/embedding_probability/(string:embedding)

    Devuelve la probabilidad de que un vector de *embedding* sea verdadero
    dentro de un *dataset_id* dado.

    :prioridad: 0
    :todo: 501 Not Implemented
    :param int dataset_id: id único del dataset
    :param list embedding: Vector de *embedding* a obtener su probabilidad
