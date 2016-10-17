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

.. http:get:: /dataset/(int:dataset_id)/

    Obtener toda la información de un dataset

    :prioridad: 0
    :param int dataset_id: id único del dataset

.. ver celery para añadir peticiones asíncronas a un "demonio" https://github.com/celery/celery/
.. http:post:: /dataset/(int:dataset_id)/train?algorithm=(int:id_algorithm)

    Entrenar un dataset con un algoritmo dado. Se usará un modelo de petición
    asíncrona, dado que puede tardar una cantidad de tiempo considerable.

    El dataset ya tiene que existir y no debe haber sido entrenado previamente

    Se pondrá la petición en una cola y se devolverá un 202 ACCPEPTED, con
    la cabecera LOCATION: rellena con una tarea (/task/{id}), que mostrará el progreso.
    Al finalizar, la tarea mostrará un 303, ya que se habrá creado un nuevo
    recurso /dataset/{id}, y la cabecera LOCATION vendrá rellena con esa URI.

    Basado en: <http://restcookbook.com/Resources/asynchroneous-operations/>

    :prioridad: 2
    :param int dataset_id: id único del dataet
    :query int id_algorithm: id del algoritmo utilizado para entrenar el dataset.


Predicción de tripletas
```````````````````````

.. http:get:: /dataset/(int:dataset_id)/similar_entities/(string:entity)?limit=(int:limit)

    Obtener *limit* entidades similares a *entity* dentro del *dataset_id*

    :prioridad: 0
    :param int dataset_id: id único del dataset
    :param string entity: Representación de la entidad
    :query int limit: Límite de entidades similares que se piden

.. http:get:: /predict/similar_entities_by_embedding/(int:dataset_id)/(string:embedding)?limit=(int:limit)

    Obtener n entidades similares dado un vector de *embedding*.

    :prioridad: 0
    :param int dataset_id: id único del dataset
    :param list embedding: Vector de *embedding* a obtener entidades similares
    :query int limit: Límite de entidades similares que se piden


.. http:get:: /predict/embedding_prob/(int:dataset_id)/(string:embedding)

    Devuelve la probabilidad de que un vector de embedding sea verdadero
    dentro de un dataset dado.

    :prioridad: 0
    :param int dataset_id: id único del dataset
    :param list embedding: Vector de *embedding* a obtener entidades similares
