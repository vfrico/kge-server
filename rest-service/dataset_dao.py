#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding:utf-8
#
# dataset_dao.py: Manages the persistence in database for dataset objects (DAO)
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
import data_access_base
from dataset_dto import DatasetDTO
from algorithm_dao import AlgorithmDAO


class DatasetDAO(data_access_base.MainDAO):
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
        # self.dataset = {
        #     "status": None,
        #     "entities": None,
        #     "relations": None,
        #     "triples": None,
        #     "algorithm": None,
        #     "id": None
        # }
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

        # Fill a DatasetDTO
        try:
            dataset_dto = DatasetDTO()
            dataset_dto.from_dict(res[0])
        except LookupError as e:  # TODO: Unknown
            return (None, e.args[0])

        return (dataset_dto, None)

    def get_binary_path(self, dataset_id):
        """Extracts from database the binary path of the dataset

        :param int dataset_id: The id of the dataset
        """
        query = "SELECT binary_dataset FROM dataset WHERE id=? ;"
        res = self.execute_query(query, dataset_id)

        if res is None or len(res) < 1:
            return None, (404, "Binary dataset of dataset (id:{}) not found".
                          format(dataset_id))
        final_path = os.path.join(self.bin_path, res[0]['binary_dataset'])
        return final_path, None

    def get_model(self, dataset_id):
        """Extracts from database the model file path

        :param int dataset_id: The id of the dataset
        """
        query = "SELECT binary_model FROM dataset WHERE id=? ;"
        res = self.execute_query(query, dataset_id)

        if res is None or len(res) < 1:
            return None, (404, "Binary model of dataset (id:{}) not found".
                          format(dataset_id))
        final_path = os.path.join(self.bin_path, res[0]['binary_model'])
        return final_path, None

    def set_model(self, dataset_id, model_path):
        """Saves on database the model path file of a dataset_id

        :param int dataset_id: The id of the dataset
        :param str model_path: The path where binary file is located
        """
        query = "UPDATE dataset SET binary_model=? WHERE id=? ;"
        res = self.execute_insertion(query, model_path, dataset_id)

        if res.rowcount == 1:
            res.close()
            return True, None
        else:
            res.close()
            return False, (400, "Failed when trying to save dataset on db")

    def build_dataset_object(self, dataset_dto):  # TODO: Maybe uneeded?
        """Returns a Dataset object if required by rest service

        This method need datasetDAO has binary_dataset variable initialized.

        :returns: a Dataset object
        :rtype: kgeserver.dataset.Dataset
        """
        if dataset_dto and dataset_dto._binary_dataset:
            dtst = dataset.Dataset()
            path = os.path.join("../datasets/", dataset_dto._binary_dataset)
            dtst.load_from_binary(path)
            return dtst
        else:
            return None

    def build_dataset_path(self, dataset_dto):  # TODO deprecated
        """Generates a relative path to the dataset from a DTO
        :deprecated: See get_binary_path
        """
        return "../datasets/" + get_binary_path._binary_dataset

    def set_search_index(self, dataset_id, index_path):
        """Saves on database the index of a dataset

        :param int dataset_id: The id of the dataset
        :param string index_path: The path on the filesystem of the index
        :returns: If operation was successful
        :rtype: tuple
        """
        query = "UPDATE dataset SET binary_index=? WHERE id=? ;"

        res = self.execute_insertion(query, index_path, dataset_id)

        if res.rowcount == 1:
            res.close()
            return True, None
        else:
            res.close()
            return False, (400, "Failed when trying to save index on db")

    def get_search_index(self, dataset_dto):
        """Returns an instantiated search index from choosen dataset.

        This method will test if dataset has a generated index.
        :returns: The search index or None
        :rtype: tuple
        """
        if dataset_dto.status < 2:
            return None, (409, "Dataset {id} has {status} status and is not "
                               "ready for search".format(**self.dataset))
        try:
            sch_in = server.SearchIndex()
            sch_in.load_from_file(dataset_dto.get_binary_index(),
                                  dataset_dto.algorithm['embedding_size'])
            return sch_in, None
        except OSError as err:
            msg = "The server has encountered an error: '{}'."
            return None, (500, msg.format(err.args))

    def get_server(self):  # TODO: Deprecated
        """Returns the server with the correct search index loaded.

        :return: The Server object or None
        :rtype: tuple
        """
        search_index, err = self.get_search_index()
        if search_index is None:
            return None, err
        else:
            return server.Server(search_index), None

    def insert_empty_dataset(self, datasetClass):  # TODO: Unknown if needed
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
                dataset_dto = DatasetDTO()
                dataset_dto.from_dict(result)
                all_datasets.append(dataset_dto)
            except LookupError as e:
                err_msg = "On dataset {0}: {1}".format(result['id'],
                                                       e.args[0][1])
                return (None, (e.args[0][0], err_msg))

        return all_datasets, None

    def get_dataset_types(self):  # TODO: This should not be here...
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

    def insert_triples(self, dataset_dto, triples_list):
        # TODO: This should not be here
        """Insert triples on the Dataset.
        """
        dtst_path = dataset_dto.get_binary_dataset()
        if dtst_path is None:
            return None, (500, "Dataset couldn't be loaded")
        dtset = dataset.Dataset()
        dtset.load_from_binary(dtst_path)
        dtset.show()

        result = dtset.load_dataset_from_json(triples_list)

        # sql = "SELECT binary_dataset FROM dataset WHERE id=?"
        # result = self.execute_query(sql, self.dataset["id"])
        # bin_file = result[0]['binary_dataset']

        dtset.show()

        result = result and\
            dtset.save_to_binary(dataset_dto.get_binary_dataset())

        return result, None

    def set_untrained(self, dataset_dto):
        """Set dataset_dto in untrained state
        """
        if dataset_dto.status is None or dataset_dto.status > 0:
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

    def set_algorithm(self, id_dataset, id_algorithm):  # GREAT!
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
