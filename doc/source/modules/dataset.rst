.. _dataset:


Dataset class
=============

The dataset class is used to create a valid object with the main idea
to be used within the Experiment class. This approach allow us to
create easily different models to be trained, leaving the complexity
to the class itself.

The main entry point is 'load_dataset_recurrently'. This will make several
HTTP requests to obtain all the dataset given a list of Wikidata ID's. At this
moment, it only uses the Wikidata Elements which are related with a BNE ID.

To save the dataset into a binary format, you should use the 'save_to_binary'
method. This will allow to open the dataset later without executing any query.

Methods
-------

Here is shown all the different methods to use with dataset class

.. automodule:: dataset
.. autoclass:: Dataset
   :members:
