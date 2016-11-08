.. _algorithm:


Algorithm module
================

This module contains several Class. The main purpose of the module is to
provide a clear training interface. It will train several models with
several distinct configs and choose the best one. After this, it will
create a ModelTrainer class ready to train the entire model.

Methods
-------

Here is shown all the different methods to use with dataset class

.. automodule:: kgeserver.algorithm
.. autoclass:: ModelTrainer
.. autoclass:: Algorithm
   :members:


Experiment class
----------------

This class is a modified version of the file which can be found on
https://github.com/mnick/holographic-embeddings/tree/master/kg/base.py,
and was created by Maximilian Nickel mnick@mit.edu.


Methods
```````

Here is shown all the different methods to use with experiment class

.. automodule:: kgeserver.experiment
.. autoclass:: Experiment
   :members:
