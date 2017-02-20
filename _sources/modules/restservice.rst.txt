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

Datasets management
```````````````````
The `/dataset` collection contains several methods to create, add triples to
the dataset, train and generate search indexes.

It also contains these main params

.. sourcecode:: json

    {"entities", "relations", "triples", "status", "algorithm"}

The ``algorithm`` parameter contains all the information the dataset are trained with.
See `/algorithm` collection to get more information about this.

Dataset will be changing its status when actions such training or indexing
are performed. The *status* can only grow up. When a changing status is taking
place, the dataset cannot be edited. In this situations, the status will be
a negative integer.

**status**: ``untrained`` -> ``trained`` -> ``indexed``

.. http:get:: /datasets/(int:dataset_id)/

    Get all the information about a dataset, given a ``dataset_id``

    **Sample request and response**

    :http:get:`/datasets/1/`

    .. sourcecode:: json

        {
        	"dataset": {
        		"relations": 655,
        		"triples": 3307248,
        		"algorithm": {
        			"id": 2,
        			"embedding_size": 100,
        			"max_epochs": null,
        			"margin": 2
        		},
        		"entities": 651759,
        		"status": 2,
        		"name": null,
        		"id": 4
        	}
        }
    :param int dataset_id: Unique *dataset_id*
    :statuscode 200: Returns all information about a dataset.
    :statuscode 404: The dataset can't be found.

.. http:post:: /datasets/(int:dataset_id)/train?algorithm=(int:id_algorithm)

    Train a dataset with a given algorithm id. The training process can be
    quite large, so this REST method uses a asynchronous model to perform
    each request.

    The response of this method will only be a ``202 ACCEPTED`` status code, with
    the ``Location:`` header filled with the task path element. See ``/tasks``
    collection to get more information about how tasks are managed on the
    service.

    The dataset must be in a 'untrained' (0) state to get this operation done.
    Also, no operation such as ``add_triples`` must be being processed.
    Otherwise, a 409 CONFLICT status code will be obtained.

    :param int dataset_id: Unique *dataset_id*
    :query int id_algorithm: The wanted algorithm to train the dataset
    :statuscode 202: The requests has been accepted to the system and a task has
                     been created. See Location header to get more information.
    :statuscode 404: The dataset or the algorithm can't be found.
    :statuscode 409: The dataset cannot be trained due to its status.

.. http:get:: /datasets/

    Gets all datasets available on the system.

    :statuscode 200: All the datasets are shown correctly

.. TODO: This method is not implemented
    .. http:get:: /dataset_types

        Obtener todos los tipos de dataset disponibles en el sistema. No pueden
        ser modificados.

        :statuscode 200: Se muestran adecuadamente los tipos


.. http:post:: /datasets?dataset_type=(int:dataset_type)

    Creates a new and empty dataset. To fill in you must use other requests.

    You also must provide ``dataset_type`` query param. This method will create
    a WikidataDataset (id: 1) by default, but you also can create different
    datasets providing a different dataset_type.

    Inside the body of the request you can provide a name and/or a description
    for the dataset. The name must be unique. For example:

    **Sample request**

    :http:post:`/datasets`

    .. sourcecode:: json

        {"name": "films", "description": "A dataset with favourite films"}

    :query int dataset_type: The dataset type to be created. 0 is for a simple
                             Dataset and 1 is for WikidataDataset (default).
    :statuscode 201: A new dataset has been created successfuly. See ``Location:``
                     header to get the id and the new resource path.
    :statuscode 409: The given name already exists on the server.


.. http:put:: /datasets/(int:dataset_id)

    Edits the description from a existing dataset.

    **Sample request**

    :http:put:`/datasets`

    .. sourcecode:: json

        {"description": "A dataset with most awarded films"}

    :param int dataset_id: Unique *dataset_id*
    :statuscode 200: The dataset has been updated successfully. The updated
                     dataset will be returned in the response.
    :statuscode 404: The provided *dataset_id* does not exist.


.. http:post:: /datasets/(int:dataset_id)/triples

    Adds a triple or a list of triples to the dataset. You must provide a JSON
    object on the request body, as shown below on the example. The name of the
    JSON object must be *triples* and must contain a list of all entities to be
    introduced inside the dataset. These entities must contain
    ``{"subject", "predicate", "object"}`` params. This notation is similar to other
    known as *head*, *label* and *tail*.

    Only triples can be added on a ``untrained`` (0) dataset.

    **Ejemplo**

    :http:post:`/datasets/6/triples`

    .. sourcecode:: json

        {"triples": [
                {
                    "subject": {"value": "Q1492"},
                    "predicate": {"value": "P17"},
                    "object": {"value": "Q29"}
                },
                {
                    "subject": {"value": "Q2807"},
                    "predicate": {"value": "P17"},
                    "object": {"value": "Q29"}
                }
            ]
        }

    :param int dataset_id: Unique *dataset_id*
    :statuscode 200: The request has been successful
    :statuscode 404: The dataset or the algorithm can't be found.
    :statuscode 409: The dataset cannot be trained due to its status.


.. http:post:: /datasets/(int:dataset_id)/generate_triples

    Adds triples to dataset doing a sequence of SPARQL queries by levels,
    starting with a seed vector. This operation is supported only by
    certain types of datasets (the default one, type=1)

    The request will use asyncronous operations. This means that the request
    will not be satisfied on the same HTTP connection. Instead, the service
    will return a `/task` resource that will be queried with the progress
    of the task.

    The ``graph_pattern`` argument must be the where part of a SPARQL query. It
    **must** contain three variables named as ``?subject``, ``?predicate``
    and ``?object``. The service will try to make a query with these names.

    You also must provide the ``levels`` to make a deep lookup of the entities
    retrieved from previous queries.

    The optional param ``batch_size`` is used
    on the first lookup for SPARQL query. For big queries you must tweak this
    parameter to avoid server errors as well as to increase performance. It is
    the LIMIT statement when doing this queries.

    **Sample request**

    .. sourcecode:: json

        {
            "generate_triples":
                {
                    "graph_pattern": "SPARQL Query",
                    "levels": 2,
                    "batch_size": 30000
                }
        }

    **Sample response**

    The ``location:`` header of the response will contain the relative URI for the
    created task resouce:

        ``location: /tasks/32``

    .. sourcecode:: json

        {
            "status": 202,
            "message": "Task 32 created successfuly"
        }

    :param int dataset_id: Unique identifier of dataset
    :statuscode 404: The provided *dataset_id* does not exist.
    :statuscode 409: The *dataset_id* does not allow this operation
    :statuscode 202: A new task has been created. See /tasks resource
                     to get more information.

.. http:post:: /datasets/(int:dataset_id)/embeddings

    Retrieve from the trained dataset the embeddings from a list of entities.

    If on the request list the user requests for a entity that does not exist,
    the response won't contain that element. The 404 error is limited to the
    dataset, not the entities inside the dataset.

    The dataset must be in trained status (>= 1), because a model must exist to
    extract triples from. If not, a 409 CONFLICT will be returned.

    This could be useful if it is used with /similar_entities endpoint, to find
    similar entities given a different embedding vector.

    **Sample request**

    :http:post:`/datasets/6/embeddings`

    .. sourcecode:: json

        {"entities": [
            "http://www.wikidata.org/entity/Q1492",
            "http://www.wikidata.org/entity/Q2807",
            "http://www.wikidata.org/entity/Q1" ]
        }

    **Sample response**

    .. sourcecode:: json

        { "embeddings": [
            [
                "Q1",
                [0.321, -0.178, 0.195, 0.816]
            ],
            [
                "Q2807",
                [-0.192, 0.172, -0.124, 0.138]
            ],
            [
                "Q1492",
                [0.238, -0.941, 0.116, -0.518]
            ]
          ]
        }

    *Note: The upper vectors are only shown as illustrative, they are not real values*

    :param int dataset_id: Unique id of the dataset
    :statuscode 200: Operation was successful
    :statuscode 404: The dataset ID does not exist
    :statuscode 409: The dataset is not on a correct status


Algorithms
``````````

The algorithm collection is used mainly to create and see the different algorithms
created on the server.

The hyperparameters that are allowed currently to tweak are:
- `embedding_size`: The size of the embeddigs the trainer will use
- ``margin``: The margin used on the trainer
- ``max_epochs``: The maximum number of iterations of the algorithm

.. http:get:: /algorithms/

    Gets a list with all the algorithms created on the service.

.. http:get:: /algorithms/(int:algorithm_id)

    Gets only one algorithm

    :param int algorithm_id: The algorithm unique identifier

.. http:post:: /algorithms/

    Create one algorithm on the service. On success, this method will return
    a 201 CREATED status code and the header parameter `Location:` filled with
    the relative path to the created resource.

    The body of the request must contain all parameters for the new algorithm.
    See the example below:

    **Sample request**

    :http:post:`/algorithms`

    .. sourcecode:: json

        {
        	"algorithm": {
        		"embedding_size": 50,
        		"margin": 2,
        		"max_epochs": 80
        	}
        }

    :statuscode 201: The request has been processed successfuly and a new
                     resource has been created. See ``Location:`` header
                     to get the new path.

Tasks
`````
The task collection stores all the information that async request need. This
collection are made mainly to get the actual state of tasks, but no to edit or
delete tasks (Not implemented).

.. http:get:: /tasks/(int:task_id)?get_debug_info=(boolean:get_debug_info)&?no_redirect=(boolean:no_redirect)

    Shows the progress of a task with a ``task_id``. The finished tasks can be
    deleted from the system without previous advise.

    Some tasks can inform to the user about its progress. It is done through
    the progress param, which has *current* and *total* relative arguments, and
    *current_steps* and *total_steps* absolute arguments. When a task involves
    some steps and the number of small tasks to be done in next step cannot
    be discovered, the current and total will only indicate progress in current
    step, and will not include previous step, expected to be already done, or next
    step which is expected to be empty.

    The resource has two optional parameters: ``get_debug_info`` and ``no_redirect``.
    The first one, ``get_debug_info`` set to true on the query params will return
    additional information from the task. The other param, ``no_redirect`` will
    avoid send a 303 status to the client to redirect to the created resource.
    Instead it will send a simple 200 status code, but with the location header
    filled.

    :param int task_id: Unique *task_id* from the task.
    :statuscode 200: Shows the status from the current task.
    :statuscode 303: The task has finished. See Location header to find the
                     resource it has created/modified. With ``no_redirect`` query
                     param set to true, the location header will be filled, but
                     a 200 code will be returned instead.
    :statuscode 404: The given *task_id* does not exist.

.. NOT IMPLEMENTED STILL...
    .. http:delete:: /tasks/(int:task_id)

        Deletes a task from database. If it is possible to stop a task which is
        started but not finished, it will be stopped and deleted. If this is not
        possible, the task resource will be kept as is, and a 409 status code will
        be sent along a reason why the task cannot be stopped.

        If the task is deleted, the status will not be queried in a future, but any
        result produced by the task (such as adding triples to a dataset), will
        be kept on its own resource.

        :prioridad: 1
        :todo: Not implemented
        :statuscode 204: The task has been deleted
        :statuscode 404: The task does not exists and cannot be deleted
        :statuscode 409: The current state of the task does not allow to delete it

Triples prediction
``````````````````

.. http:get:: /datasets/(int:dataset_id)/similar_entities/(string:entity)?limit=(int:limit)?search_k=(int:search_k)
.. http:post:: /datasets/(int:dataset_id)/similar_entities?limit=(int:limit)?search_k=(int:search_k)

    Get the *limit* entities most similar to a *entity* inside a *dataset_id*.
    The given number in *limit* excludes the entity given itself.

    The POST method allows any representation of the wanted resource. See the
    example below. You can provide an entity as an URI or other similar
    representation, even an embedding. The type param inside entity JSON object
    must be "uri" for a URI or similar representation and "embedding" for an
    embedding.

    The ``search_k`` param is used to tweak the results of the search. When this
    value is greater, the precission of the results are also greater, but the
    time it takes to find the response is also bigger.

    **Sample request**

    :http:get:`/datasets/7/similar_entities?limit=1&search_k=10000`

    .. sourcecode:: json

        { "entity":
              {"value": "http://www.wikidata.org/entity/Q1492", "type": "uri"}
        }

    **Sample response**

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


    :param int dataset_id: Unique id of the dataset
    :query int limit: Limit of similar entities requested. By default this is
                      set to 10.
    :query int search_k: Max number of trees where the lookup is performed.
                         This increase the result quality, but reduces the
                         performance of the request. By default is set to -1
    :statuscode 200: The request has been performed successfully
    :statuscode 404: The dataset or the entity can't be found

.. http:post:: /datasets/(int:dataset_id)/distance

    Returns the distance between two elements. The lower this is, most probable
    to be both the same triple. The minimum distance is 0.

    **Request Example**

    :http:post:`/datasets/0/similar_entities`

    .. sourcecode:: json

        {
            "distance": [
                 "http://www.wikidata.org/entity/Q1492",
                 "http://www.wikidata.org/entity/Q5682"
            ]
        }

    *HTTP Response*

    .. sourcecode:: json

        {
            "distance": 1.460597038269043
        }

    :param int dataset_id: Unique id of the dataset
    :statuscode 200: The request has been performed successfully
    :statuscode 404: The dataset or the entity can't be found

.. TODO: It is unknown the method on kgeserver library to get the wanted value
    .. http:get:: /datasets/(int:dataset_id)/embedding_probability/(string:embedding)

        Devuelve la probabilidad de que un vector de *embedding* sea verdadero
        dentro de un *dataset_id* dado.

        :prioridad: 0
        :todo: 501 Not Implemented
        :param int dataset_id: Unique id of the dataset
        :param list embedding: Vector de *embedding* a obtener su probabilidad
