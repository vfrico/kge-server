.. _dataset:


Dataset module
==============

Introduction
------------

The dataset class is used to create a valid object with the main idea
to be used within the Experiment class. This approach allow us to
create easily different models to be trained, leaving the complexity
to the class itself.

You have different types of datasets. The main class of datasets is
kgeserver.dataset.Dataset_, but this will allow to create basic datasets from
a csv or JSON file, without any restriction of triples or relations that may not
be useful for the dataset and makes the binary file very big.

You have several Datasets that work with some of the most well known and free
knowledge graphs on Internet. Those are:

- WikidataDataset_:
  This class can manage all queries from the Wikidata portal,
  including wikidata id's prepended with Q, like in ``Q1492``.
  It is fully ready to perform any you need with really good results.

- ESDBpediaDataset_:
  This class is not as well ready as Wikidata, but is able to perform
  SPARQL Queries to get entities and relations on the Spanish DBpedia.

The most interesting feature that those Dataset class provides is to build a
local dataset with making multiple parallel queries to the SPARQL endpoints
to retrieve all information about a given topic. You can start by getting
a *seed_vector* of the entities you want to focus on and then build a
n levels graph by quering each entity to its relations with other new entities.

The seed vector can be obtained through the load_from_graph_pattern_ method.
After that, you should save it on a variable and pass it as an argument to
the load_dataset_recurrently_ method. This is the function that will make
several queries to fill the dataset with the desried levels of depth.

To save the dataset into a binary format, you should use the save_to_binary_
method. This will allow to open_ the dataset later without executing any query.

.. _open: #kgeserver.dataset.Dataset.load_from_binary
.. _save_to_binary: #kgeserver.dataset.Dataset.save_to_binary
.. _kgeserver.dataset.Dataset: #kgeserver.dataset.Dataset
.. _WikidataDataset: #kgeserver.wikidata_dataset.WikidataDataset
.. _load_from_graph_pattern: #kgeserver.dataset.Dataset.load_from_graph_pattern
.. _load_dataset_recurrently: #kgeserver.dataset.Dataset.load_dataset_recurrently

Binary Dataset
``````````````

The binary file of datasets are created using Pickle. It basicaly
stores all the entities, all the relations and all the triples. It also
stores some extra information to be able to *rebuild* the dataset later. The
binary file is stored like a python dictionary which contains the following
keys: ``__class__``, ``relations``, ``test_subs``, ``valid_subs``, ``train_subs``
and ``entities``.

The ``relations`` and ``entities`` entries are lists, and it's length indicates
us the number of relations or entities the dataset has. The ``__class__`` entry
is for internal use of the class kgeserver.dataset. The triples are stored
in three different entries, called ``test_subs``, ``valid_subs`` and
``train_subs``. Those subsets are created to be used for the next module, the
algorithm module, wich will evaluate the dataset. This is a common practice
when machine learning algorithms are used. If you need all the triples, they can
be joined easily in python by adding the three lists between them:

::

    triples = dataset["test_subs"] + dataset["valid_subs"] + dataset["train_subs"]

The split ratio commonly used is to use the 80% of the triples to train and the
rest of triples are divided equally between *test* and *valid* triples. You can
create a different split providing a value to dataset.train_split_.
It also exists an dataset.improved_split_ method wich takes a bit longer to create,
but it is better to test the dataset.


.. _dataset.train_split: #kgeserver.dataset.Dataset.train_split
.. _dataset.improved_split: #kgeserver.dataset.Dataset.improved_split

Dataset Class
-------------

This class is used to create basic datasets. They can be filled with csv
files, JSON files or even simple sparql queries.

Methods
```````
Here is shown all the different methods to use with dataset class

.. automodule:: kgeserver.dataset
.. autoclass:: Dataset
    :members:
    :special-members:
    :private-members:


.. _dataset.get_seed_vector: #kgeserver.dataset.Dataset.get_seed_vector
.. _dataset.load_dataset_recurrently: #kgeserver.dataset.Dataset.load_dataset_recurrently
.. _dataset._process_entity: #kgeserver.dataset.Dataset._process_entity


WikidataDataset
---------------

This class will enable you to generate a dataset from the information present in
Wikidata Knowledge base. This class only needs to get a simple graph pattern to
get started to build a dataset. An example of graph pattern that should be passed
to WikidataDataset.load_from_graph_pattern_ method:

::

    "{ ?subject wdt:P950 ?bne . ?subject ?predicate ?object }"


It is required to bind at least three variables, because they will be used in
the next queries. Those variables should be called "?subject",
"?predicate" and "?object".


.. _WikidataDataset.load_from_graph_pattern: #kgeserver.wikidata_dataset.WikidataDataset.load_from_graph_pattern

Methods
```````

.. automodule:: kgeserver.wikidata_dataset
.. autoclass:: WikidataDataset
    :members:
    :special-members:
    :private-members:



ESDBpediaDataset
----------------
In a similar way that it occurs with WikidataDataset_, this class will allow
to you to create datasets from the spanish DBpedia. The graph pattern you
should pass to ESDBpediaDataset.load_from_graph_pattern_ method looks like this:

::

    { ?subject dcterms:subject <http://es.dbpedia.org/resource/Categoría:Trenes_de_alta_velocidad> . ?subject ?predicate ?object" }


As for WikidataDataset_, you need to bind the same three variables: "?subject",
"?predicate" and "?object".

.. _WikidataDataset: #kgeserver.wikidata_dataset.WikidataDataset
.. _ESDBpediaDataset.load_from_graph_pattern: #kgeserver.dbpedia_dataset.ESDBpediaDataset.load_from_graph_pattern


Methods
```````

.. automodule:: kgeserver.dbpedia_dataset
.. autoclass:: ESDBpediaDataset
    :members:
    :special-members:
    :private-members:
