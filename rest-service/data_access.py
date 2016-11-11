#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding:utf-8
#
# data_access.py: Contains several DAO for different objects on the service
# Copyright (C) 2016  Víctor Fernández Rico <vfrico@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import os
import time
import sqlite3
import redis
import json
import kgeserver.server as server
import kgeserver.dataset as dataset
import kgeserver.wikidata_dataset as wikidata_dataset
database_file = "server.db"


class MainDAO():
    def __init__(self, database_file="server.db"):
        "Comprueba si existe la base de datos y/o la inicializa"

        self.database_file = database_file

        # Create the file itself
        try:
            os.stat(self.database_file)
        except (OSError, FileNotFoundError) as err:
            # File does not exist. Create
            print("Create file")
            f = open(self.database_file, "w+")
            f.close()
            self.connection = sqlite3.connect(self.database_file)
            self.build_basic_db()

        # Path where all binary files have its relative path
        self.bin_path = "../datasets/"

        self.connection = sqlite3.connect(self.database_file)

    def build_basic_db(self):

        self.execute_query("CREATE TABLE algorithm "
                           "(id INTEGER UNIQUE PRIMARY KEY, "
                           "embedding_size INTEGER, "
                           "margin FLOAT) ; ")

        self.execute_query("CREATE TABLE dataset "
                           "(id INTEGER UNIQUE PRIMARY KEY, "
                           "binary_dataset TEXT, "
                           "binary_model TEXT, "
                           "binary_index TEXT,"
                           "algorithm INTEGER, "
                           "entities INTEGER, "
                           "relations INTEGER, "
                           "triples INTEGER, "
                           "status INTEGER, "
                           "FOREIGN KEY(algorithm) REFERENCES algorithm(id)"
                           ");")

        self.execute_query("CREATE TABLE tasks "
                           "(id INTEGER UNIQUE PRIMARY KEY, "
                           "celery_uuid TEXT, "
                           "progress_file TEXT "
                           ") ; ")

        default_datasets = [
                        {"id": 0, "binary_dataset": 'wikidata_25k.bin',
                         "binary_model": "",
                         "binary_index": 'wikidata_25k.annoy.bin',
                         "status": 0, 'algorithm': 0},
                        {"id": 1, "binary_dataset": '4levels.bin',
                         "binary_model": 'modelo_guardado.bin',
                         "binary_index": 'annoyIndex.500.bin',
                         "status": 2, 'algorithm': 0},
                        {"id": 2, "binary_dataset": '4levels.bin',
                         "binary_model": 'modelo_guardado.bin',
                         "binary_index": 'annoyIndex.600.bin',
                         "status": 2, 'algorithm': 0},
                        {"id": 3, "binary_dataset": 'newDataset4lvl.bin',
                         "binary_model": 'Unnuevomodeloentrenado.bin',
                         "binary_index": 'unuevoAnnoy.600.bin',
                         "status": 2, 'algorithm': 1},
                        {"id": 4, "binary_dataset": 'newDataset4lvl.bin',
                         "binary_model": 'modelo_newDataset4lvl_m2.bin',
                         "binary_index": 'Annoy.nuevo.600.m2.bin',
                         "status": 2, 'algorithm': 2}
                        ]
        default_algorithms = [
                        {"id": 0, "embedding_size": 100},
                        {"id": 1, "embedding_size": 100,
                         "margin": 1.0},
                        {"id": 2, "embedding_size": 100,
                         "margin": 2.0},
                        {"id": -1, "embedding_size": -1}
        ]
        for alg in default_algorithms:
            self.execute_query(
                "INSERT INTO algorithm {0} VALUES {1} ;"
                .format(tuple(alg.keys()), tuple(alg.values())))
        for dtset in default_datasets:
            self.execute_query(
                "INSERT INTO dataset {0} VALUES {1} ;"
                .format(tuple(dtset.keys()), tuple(dtset.values())))

    def execute_query(self, query, *args):
        """Executes a query and returns a list of rows

        This method is intended mainly to get results from a SELECT query. To
        execute an INSERT statement or similar, please, see `execute_insertion`

        :param string query: The SQL query.
        :param list *args: A list for formatting query string.
        :returns: A list of rows from a query.
        :rtype: list
        """
        connection = self.connection

        # The row factory returns a richer object to user, similar to dict
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        # Before execute a SQL query is necessary to turn on
        # the foreign_keys restrictions
        # cursor.execute("PRAGMA foreign_keys = ON;")
        # Execute the *real* query
        cursor.execute(query, args)

        # cursor values will be lost when is closed, saving in auxiliar var.
        row = cursor.fetchall()
        connection.commit()
        cursor.close()

        return row

    def execute_insertion(self, query, *args):
        """Executes a query and returns the entire cursor

        This is intended to return the cursor, which needs to be closed after
        the results are fetched. This method can be used both for INSERT SQL
        statement or others like SELECT.

        :param string query: The SQL query.
        :return: A cursor that must be closed
        :rtype: sqlite3.Cursor
        """
        connection = self.connection

        # The row factory returns a richer object to user, similar to dict
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        # Before execute a SQL query is necessary to turn on
        # the foreign_keys restrictions
        # cursor.execute("PRAGMA foreign_keys = ON;")
        # Execute the *real* query
        cursor.execute(query, args)

        connection.commit()
        return cursor  # Must be closed outside function


class DatasetDAO(MainDAO):
    """Object to interact between the data storage and returns valid objects

    All methods that shows a "return tuple", it returns a pair, where first
    element is an object if no error found or None if error are found. Details
    of the error can be queried on the other element of the pair.

    Example without error: (dataset.Dataset, None)
    Example with error: (None, (404, "Not found on database"))
    """

    def __init__(self, database_file="server.db"):
        """Instantiates the object and creates *private* variables

        :param string database_file: A database file if differs from default.
        """
        super(DatasetDAO, self).__init__(database_file=database_file)
        self.dataset = {
            "status": None,
            "entities": None,
            "relations": None,
            "triples": None,
            "algorithm": None,
            "id": None
        }
        self.binary_dataset = None
        self.binary_model = None
        self.binary_index = None

    def get_dataset_by_id(self, dataset_id):
        """Returns a dataset information given its id

        :return: A dataset dictionary or none
        :rtype: tuple
        """
        query = "SELECT * FROM dataset WHERE id={0} ;".format(dataset_id)
        res = self.execute_query(query)
        # Query has return nothing
        if res is None or len(res) == 0:
            return None, (404, "Dataset {} not found".format(dataset_id))

        try:
            dtst_dict = self.build_dataset_info(res[0])
        except LookupError as e:
            return (None, e.args[0])

        return (dtst_dict, None)

    def build_dataset_info(self, result_dict):
        """Given a result dict, with proper fields, builds a datasetDAO

        :param dict result_dict: A dict with all fields required
        :return: A dataset dictionary or None
        :rtype: dict
        """  # INFO:This method is intended ONLY to fill a dataset dict.
        # Query has an object
        self.binary_dataset = result_dict['binary_dataset']
        self.binary_model = result_dict['binary_model']
        self.binary_index = result_dict['binary_index']
        self.dataset['status'] = result_dict['status']
        self.dataset['id'] = int(result_dict['id'])

        if result_dict['triples'] and result_dict['relations'] and\
           result_dict['entities']:
            # These fields are filled and can be readable
            self.dataset['triples'] = result_dict['triples']
            self.dataset['entities'] = result_dict['entities']
            self.dataset['relations'] = result_dict['relations']
        else:
            # Fields should be readed from file
            dtst = dataset.Dataset()
            dtst.load_from_binary(self.bin_path+self.binary_dataset)
            self.dataset['triples'] = len(dtst.subs)
            self.dataset['entities'] = len(dtst.entities)
            self.dataset['relations'] = len(dtst.relations)

        alg_dao = AlgorithmDAO()
        algorithm, err = alg_dao.get_algorithm_by_id(result_dict['algorithm'])
        if algorithm is None:
            raise LookupError(err)
        self.dataset['algorithm'] = algorithm

        return self.dataset

    def build_dataset_object(self):
        """Returns a Dataset object if required by rest service

        This method need datasetDAO has binary_dataset variable initialized.

        :returns: a Dataset object
        :rtype: kgeserver.dataset.Dataset
        """
        if self.dataset and self.binary_dataset:
            dtst = dataset.Dataset()
            dtst.load_from_binary(self.bin_path+self.binary_dataset)
            return dtst
        else:
            return None

    def build_dataset_path(self):
        return self.bin_path + self.binary_dataset

    def get_search_index(self):
        """Returns an instantiated search index from choosen dataset.

        This method will test if dataset has a generated index.
        :returns: The search index or None
        :rtype: tuple
        """
        if self.dataset['status'] < 2:
            return None, (409, "Dataset {id} has {status} status and is not "
                               "ready for search".format(**self.dataset))
        try:
            sch_in = server.SearchIndex()
            sch_in.load_from_file(self.bin_path + self.binary_index,
                                  self.dataset['algorithm']['embedding_size'])
            return sch_in, None
        except OSError as err:
            msg = "The server has encountered an error: '{}'."
            return None, (500, msg.format(err.args))

    def get_server(self):
        """Returns the server with the correct search index loaded.

        :return: The Server object or None
        :rtype: tuple
        """
        search_index, err = self.get_search_index()
        if search_index is None:
            return None, err
        else:
            return server.Server(search_index), None

    def insert_empty_dataset(self, datasetClass):
        """Creates an empty dataset on database.

        :param kgeserver.dataset.Dataset datasetClass: The class of the dataset
        :return: The id of dataset created, or None
        :rtype: tuple
        """
        unique_name = str(int(time.time()))+".bin"
        sql_sentence = ("INSERT INTO dataset (id, binary_dataset, algorithm, "
                        "status) VALUES (NULL, '"+unique_name+"', -1, 0)")

        newdataset = datasetClass()
        self.binary_dataset = unique_name
        newdataset.save_to_binary(self.bin_path+unique_name)

        result = self.execute_insertion(sql_sentence)
        rowid = result.lastrowid
        result.close()

        # Add default status
        self.set_untrained()
        return rowid, None

    def get_all_datasets(self):
        """Queries the DB to retrieve all datasets

        :returns: A list of datasets objects
        :rtype: tuple
        """
        sql_getall = "SELECT * FROM dataset"
        results = self.execute_query(sql_getall)
        if results is None:
            return None, (404, "Any dataset found")

        # Store all datasets dictionaries
        all_datasets = []
        for result in results:
            try:
                dtst_dict = self.build_dataset_info(result)
                all_datasets.append(dtst_dict.copy())
            except LookupError as e:
                err_msg = "On dataset {0}: {1}".format(result['id'],
                                                       e.args[0][1])
                return (None, (e.args[0][0], err_msg))

        return all_datasets, None

    def get_dataset_types(self):
        """Stores the different datasets that can be created

        :returns: A list of objects
        :rtype: list
        """
        return [
            {
                "id": 0,
                "name": "dataset",
                "class": dataset.Dataset
            },
            {
                "id": 1,
                "name": "WikidataDataset",
                "class": wikidata_dataset.WikidataDataset
            }
        ]

    def insert_triples(self, triples_list):
        """Insert triples on the Dataset.
        """
        dtst = self.build_dataset_object()
        if dtst is None:
            return None, (500, "Dataset couldn't be loaded")
        dtst.show()
        result = dtst.load_dataset_from_json(triples_list)

        sql = "SELECT binary_dataset FROM dataset WHERE id=?"
        result = self.execute_query(sql, self.dataset["id"])
        bin_file = result[0]['binary_dataset']

        dtst.show()

        result = result and dtst.save_to_binary(self.bin_path+bin_file)

        return result, None

    def is_untrained(self):
        """Check if dataset is in untrained state

        Should return True if status is 0 or 1

        :return: True if dataset is in untrained state
        :rtype: tuple
        """
        dataset_status = self.dataset['status']
        if dataset_status is None:
            return None, (500, "Dataset not fully loaded")
        elif dataset_status < 2 and dataset_status >= 0:
            return True, None
        else:
            return False, None

    def set_untrained(self):
        """Set current dataset in untrained state
        """
        if not self.dataset["id"]:
            return None, (500, "Dataset not fully loaded")

        curr_status = self.dataset['status']
        if curr_status is None or curr_status > 0:
            return None, (409, "Dataset can not be updated to untrained state")
        else:
            ret, err = self.set_status(self.dataset["id"], 0)
            return ret, err

    def set_status(self, id_dataset, status):
        """Set the dataset in untrained status

        The status must be between [-2, 2].

        :param int id_dataset: The id of the dataset to be changed
        :param int status: The new status of the dataset
        :return: True if operation was successful
        :rtype: tuple
        """
        try:
            if status >= 3:
                return False, (409, "The status must be an integer [-2, 2]")
        except TypeError:
            return False, (409, "The status must be an integer or valid type")

        query = "UPDATE dataset SET status=? WHERE id=? ;"

        res = self.execute_insertion(query, status, id_dataset)
        if res.rowcount == 1:
            res.close()
            return True, None
        else:
            res.close()
            return False, (404, "Some of your variables are not correct")

    def set_algorithm(self, id_dataset, id_algorithm):
        """Changes the algorithm used on the dataset

        :param int id_dataset: The id of dataset to Change
        :param int id_algorithm: The id of the new algorithm
        :return: If the operation was successful
        :rtype: tuple
        """
        query = "UPDATE dataset SET algorithm=? WHERE id=? ;"

        res = self.execute_insertion(query, id_algorithm, id_dataset)
        if res.rowcount == 1:
            res.close()
            return True, None
        else:
            res.close()
            return False, (404, "Some of your variables are not correct")


class AlgorithmDAO(MainDAO):
    def __init__(self, database_file="server.db"):
        super(AlgorithmDAO, self).__init__(database_file=database_file)
        self.algorithm = {}

    def get_algorithm_by_id(self, algorithm_id):
        query = "SELECT * FROM algorithm WHERE id=?"
        res = self.execute_query(query, algorithm_id)

        if res is None or len(res) < 1:
            return None, (404, "Algorithm "+str(algorithm_id)+" not found")

        for key in res[0].keys():
            self.algorithm[key] = res[0][key]

        return self.algorithm, None

    def get_all_algorithms(self):
        query = "SELECT * FROM algorithm"

        res = self.execute_query(query)

        algorithm_list = []

        for row in res:
            algorithm = {}
            for key in row.keys():
                algorithm[key] = row[key]
            algorithm_list.append(algorithm)

        return algorithm_list, None

    def insert_algorithm(self, algorithm_dict):
        """Inserts a new Algorithm in the service

        To avoid UNIQUE constraint fails, this method will delete the id on
        the dict if provided.

        :param dict algorithm_dict: The algorithm in form of dict
        :returns: The id of algorithm created
        :rtype: Tuple
        """
        query = "INSERT INTO algorithm {0} VALUES ({1})"

        # Build a query that prevents SQL injection
        values_tuple = []
        values_protect = ""
        param_tuple = []
        for param in algorithm_dict:
            if param == "id":
                continue
            param_tuple.append(param)
            values_tuple.append(algorithm_dict[param])
            values_protect += "?,"
        values_protect = values_protect[:-1]  # Remove last comma

        query = query.format(tuple(param_tuple), values_protect)
        try:
            result = self.execute_insertion(query, *values_tuple)
        except sqlite3.OperationalError as err:
            return None, (400, "One of the parameters is not valid. "+str(err))
        rowid = result.lastrowid
        result.close()

        return rowid, None


class RedisBackend:
    """Creates a wrapper for redis to manage dicts inside Redis

    Reads Redis configuration from environment variables. These variables
    are intended to be created with docker.
        * REDIS_PORT_6379_TCP_ADDR
        * REDIS_PORT_6379_TCP_PORT
    """
    def __init__(self):
        # Reads REDIS conf from environment variables
        port = os.environ['REDIS_PORT_6379_TCP_PORT']
        host = os.environ['REDIS_PORT_6379_TCP_ADDR']

        self.connection = redis.StrictRedis(host=host, port=port, db=0)

    def get(self, key):
        task_str = self.connection.get(key)
        if task_str is None:
            return None
        else:
            return json.loads(task_str.decode("utf-8"))

    def set(self, key, value):
        task_str = json.dumps(value)
        return self.connection.set(key, task_str.encode("utf-8"))

    def incr(self, key):
        return self.connection.incr(key)


class TaskDAO():
    """Manages the Task resource from Redis KeyStore database.

    To keep the number of tasks that exists on redis, a key named tasks will
    be created. It will only contain an integer to be incremented with every
    task created.
    """
    def __init__(self, backend=RedisBackend()):
        self.task = {"celery_uuid": None,
                     "id": None,
                     "next": None}

        self.redis = backend

    def redis_id(self):
        return self.redis_id_build(self.task["id"])

    def redis_id_build(self, id):
        return "task:{}".format(id)

    def get_task_by_id(self, task_id):
        return self.redis.get(self.redis_id_build(task_id)), None

    def add_task_by_uuid(self, task_uuid):
        self.task["id"] = self.redis.incr("tasks")
        self.task["celery_uuid"] = task_uuid
        self.redis.set(self.redis_id(), self.task)
        return self.task, None

    def update_task(self, task):
        self.redis.set(self.redis_id_build(task["id"]), task)
