#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding:utf-8
#
# dataset_dao.py: Manages the persistence in database for dataset objects (DAO)
# Copyright (C) 2016 - 2017 Víctor Fernández Rico <vfrico@gmail.com>
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
from pathlib import PurePath
import kgeserver.server as server
import kgeserver.dataset as dataset
import kgeserver.wikidata_dataset as wikidata_dataset
import kgeserver.dbpedia_dataset as dbpedia_dataset
import data_access.data_access_base as data_access_base
from data_access.dataset_dto import DatasetDTO
from data_access.algorithm_dao import AlgorithmDAO

RUNNING_TASK_MASK = 0b0001
TRAINED_MASK = 0b0010
INDEXED_MASK = 0b0100
SEARCHINDEXED_MASK = 0b1000


class DatasetDAO(data_access_base.MainDAO):
    """Object to interact between the data storage and returns valid objects

    All methods that shows a "return tuple", it returns a pair, where first
    element is an object if no error found or None if error are found. Details
    of the error can be queried on the other element of the pair.

    Example without error: (dataset.Dataset, None)
    Example with error: (None, (404, "Not found on database"))
    """

    def __init__(self):
        """Instantiates the object and creates *private* variables

        :param string database_file: A database file if differs from default.
        """
        super(DatasetDAO, self).__init__()
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

    def get_dataset_by_id(self, dataset_id, use_cache=True):
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
            dataset_dto.from_dict(res[0], use_cache=use_cache)
            # Update cache
            if not use_cache:
                self.update_dataset_stats(dataset_dto.id, dataset_dto.triples,
                                          dataset_dto.entities,
                                          dataset_dto.relations)

        except LookupError as e:
            return (None, e.args[0])

        return (dataset_dto, None)

    def get_all_datasets(self, use_cache=True):
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
                dataset_dto.from_dict(result, use_cache=use_cache)
                if not use_cache:
                    self.update_dataset_stats(dataset_dto.id,
                                              dataset_dto.triples,
                                              dataset_dto.entities,
                                              dataset_dto.relations)
                all_datasets.append(dataset_dto)
            except LookupError as e:
                err_msg = "On dataset {0}: {1}".format(result['id'],
                                                       e.args[0][1])
                return (None, (e.args[0][0], err_msg))

        return all_datasets, None

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
        # Substract to the model_path the relative bin_path
        rel_model_path = PurePath(model_path).relative_to(self.bin_path)
        query = "UPDATE dataset SET binary_model=? WHERE id=? ;"
        res = self.execute_insertion(query, str(rel_model_path), dataset_id)

        if res.rowcount == 1:
            res.close()
            return True, None
        else:
            res.close()
            return False, (400, "Failed when trying to save dataset on db")

    def set_name(self, dataset_id, dataset_name):
        """Saves the dataset with a new name

        This method will not change the name of binary files on namespace.
        It is intended only to help user locate and understand better the
        content of a dataset.

        :param int dataset_id: The id of the dataset
        :param str dataset_name: The new name of the dataset
        :return: If operation was successful
        :rtype: tuple
        """
        query = "UPDATE dataset SET name=? WHERE id=? ;"
        res = self.execute_insertion(query, dataset_name, dataset_id)

        if res.rowcount == 1:
            res.close()
            return True, None
        else:
            res.close()
            return False, (500, "Failed when trying to save dataset on db")

    def get_name(self, dataset_id):
        """Gets the current name of a given dataset

        This method will not change the name of binary files on namespace.
        It is intended only to help user locate and understand better the
        content of a dataset.

        :param int dataset_id: The id of the dataset
        :return: The dataset name
        :rtype: tuple(string, err)
        """
        query = "SELECT name FROM dataset WHERE id=? ;"
        res = self.execute_query(query, dataset_id)

        if res is None or len(res) < 1 or res[0]['name']:
            return None, (404, "Name of dataset (id:{}) not found".
                          format(dataset_id))
        return res[0]['name'], None

    def set_description(self, dataset_id, dataset_description):
        """Updates the dataset description

        This method will not change the name of binary files on namespace.
        It is intended only to help user locate and understand better the
        content of a dataset.

        :param int dataset_id: The id of the dataset
        :param str dataset_name: The new name of the dataset
        :return: If operation was successful
        :rtype: tuple
        """
        query = "UPDATE dataset SET description=? WHERE id=? ;"
        res = self.execute_insertion(query, dataset_description, dataset_id)

        if res.rowcount == 1:
            res.close()
            return True, None
        else:
            res.close()
            return False, (500, "Failed when trying to save dataset on db")

    def get_description(self, dataset_id):
        """Gets the current description of a given dataset

        This method will not change the name of binary files on namespace.
        It is intended only to help user locate and understand better the
        content of a dataset.

        :param int dataset_id: The id of the dataset
        :return: The dataset description
        :rtype: tuple(string, err)
        """
        query = "SELECT description FROM dataset WHERE id=? ;"
        res = self.execute_query(query, dataset_id)

        if res is None or len(res) < 1 or res[0]['description']:
            return None, (404, "Description of dataset (id:{}) not found".
                          format(dataset_id))
        return res[0]['description'], None

    def build_dataset_object(self, dataset_dto):  # TODO: Maybe uneeded?
        """Returns a Dataset object if required by rest service

        This method need datasetDAO has binary_dataset variable initialized.

        :returns: a Dataset object
        :rtype: kgeserver.dataset.Dataset
        """
        if dataset_dto and dataset_dto._binary_dataset:
            dtst = dataset.Dataset()
            path = os.path.join(self.bin_path, dataset_dto._binary_dataset)
            dtst.load_from_binary(path)
            return dtst
        else:
            return None

    # def build_dataset_path(self, dataset_dto):  # TODO deprecated
    #     """Generates a relative path to the dataset from a DTO
    #     :deprecated: See get_binary_path
    #     """
    #     return self.bin_path + get_binary_path._binary_dataset

    def set_search_index(self, dataset_id, index_path):
        """Saves on database the index of a dataset

        :param int dataset_id: The id of the dataset
        :param string index_path: The path on the filesystem of the index
        :returns: If operation was successful
        :rtype: tuple
        """
        # Substract to the index_path the relative bin_path
        rel_index_path = PurePath(index_path).relative_to(self.bin_path)
        query = "UPDATE dataset SET binary_index=? WHERE id=? ;"

        res = self.execute_insertion(query, str(rel_index_path), dataset_id)

        if res.rowcount == 1:
            res.close()
            return True, None
        else:
            res.close()
            return False, (400, "Failed when trying to save index on db")

    def get_search_index(self, dataset_dto, ignore_status=False):
        """Returns an instantiated search index from choosen dataset.

        This method will test if dataset has a generated index.
        :returns: The search index or None
        :rtype: tuple
        """
        # Dataset must be on indexed status
        if dataset_dto.status & INDEXED_MASK == 0 and not ignore_status:
            return None, (409, "Dataset {id} has {status} status and is not "
                          "ready for search".format(**dataset_dto.to_dict()))
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

    def insert_empty_dataset(self, datasetClass, name=None, description=None):
        """Creates an empty dataset on database.

        If name is not provided, dataset will use the current timestamp as
        name instead

        :param kgeserver.dataset.Dataset datasetClass: The class of the dataset
        :param str name: The name of the dataset
        :return: The id of dataset created, or None
        :rtype: tuple
        """
        # Check first if it does not exist a dataset with the same name
        if name is not None:
            dtsid, err = self.get_dataset_by_name(name)
            if dtsid is not None:
                return None, (409, ("A dataset with name {} already exists "
                                    "with id {}").format(name, dtsid.id))
            unique_name = "{0}/{0}_{1}".format(name, str(int(time.time())))
            bin_name = unique_name + ".bin"

        else:
            name = str(int(time.time()))
            unique_name = "{0}/{0}".format(name)
            bin_name = unique_name + ".bin"

        try:
            os.makedirs(os.path.join(self.bin_path, name))
        except FileExistsError:
            return None, (500, ("The server already contains a dataset with "
                                "{} name, but database cannot locate to which "
                                "dataset it correspond. Try to delete the "
                                "dataset folder or change the name of the "
                                "dataset.").format(name))
        sql_sentence = ("INSERT INTO dataset (id, binary_dataset, "
                        "algorithm, status, name, dataset_type) VALUES "
                        "(NULL, '" + bin_name + "', NULL, 0, ?, ?);")
        result = self.execute_insertion(
            sql_sentence, name, datasetClass.__name__)

        newdataset = datasetClass()
        self.binary_dataset = unique_name
        dtst_path = os.path.join(self.bin_path, bin_name)
        newdataset.save_to_binary(dtst_path)
        rowid = result.lastrowid
        result.close()

        if description is not None:
            self.set_description(rowid, description)
        return rowid, None

    def get_dataset_types(self):  # TODO: This should not be here...
        """Stores the different datasets that can be created

        :returns: A list of objects
        :rtype: list
        """
        return [
            {
                "id": 0,
                "name": "Dataset",
                "class": dataset.Dataset
            },
            {
                "id": 1,
                "name": "WikidataDataset",
                "class": wikidata_dataset.WikidataDataset
            },
            {
                "id": 2,
                "name": "ESDBpediaDataset",
                "class": dbpedia_dataset.ESDBpediaDataset
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
        print("dataset_dao.set_untrained() is DEPRECATED")
        if dataset_dto.status is None or\
           dataset_dto.status & RUNNING_TASK_MASK != 0:
            return None, (409, "Dataset can not be updated to untrained state")
        else:
            ret, err = self.set_status(self.dataset["id"], 0)
            return ret, err

    def update_status(self, id_dataset, newStatus, statusAnd=0b1111):
        """Mask the actual dataset status with a new one"""
        query = "SELECT status FROM dataset WHERE id=? ;"
        res = self.execute_query(query, id_dataset)
        if res is None or len(res) < 1:
            return None, (404, "Status of dataset (id:{}) not found".
                          format(id_dataset))
        return self.set_status(id_dataset,
                               (res[0]['status'] | newStatus) & statusAnd)

    def set_status(self, id_dataset, status):
        """Changes the dataset status to new status

        Status must be a binary integer, between 0b0000 and 0b1111
            * bit 0b0001: Running task
            * bit 0b0010: Trained dataset
            * bit 0b0100: Service indexed (Annoy)
            * bit 0b1000: Search indexed (Elasticsearch)

        Any of this binary values can be & to indicate a multi-status.

        :param int id_dataset: The id of the dataset to be changed
        :param int status: The new status of the dataset
        :return: True if operation was successful
        :rtype: tuple
        """
        try:
            if not 0 <= status < 16:
                return False, (409, "The status must be an integer [0, 15]")
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

    def get_dataset_by_name(self, dataset_name):
        query = "SELECT * FROM dataset WHERE name=? ;"
        res = self.execute_query(query, dataset_name)

        if res is None or len(res) == 0:
            return None, (404, "Dataset {} not found".format(dataset_name))

        # Fill a DatasetDTO
        try:
            dataset_dto = DatasetDTO()
            dataset_dto.from_dict(res[0])
        except LookupError as e:
            return (None, 404, e.args[0])

        return dataset_dto, None

    def update_dataset_stats(self, dataset_id, triples, entities, relations):
        query = ("UPDATE dataset SET triples = ?, entities = ?, relations = ?"
                 "WHERE id=?")
        res = self.execute_insertion(query, triples, entities, relations,
                                     dataset_id)
        print("Updating dataset stats")
        if res.rowcount == 1:
            res.close()
            return True, None
        else:
            res.close()
            return False, (404, "Some of your variables are not correct")

    def delete_dataset(self, dataset_id):
        """This method will delete the given dataset_id from database and
        will return all files stored by it, to delete them in a higher level.

        :param int dataset_id: The dataset id
        :return: A list of binary files or None
        :rtype: tuple
        """
        lookup_query = ("SELECT binary_dataset, binary_model, binary_index, "
                        "name FROM dataset WHERE id=? ;")
        delete_query = ("DELETE FROM dataset WHERE id = ? ;")

        res = self.execute_query(lookup_query, dataset_id)
        try:
            bin_list = [bin_file for bin_file in res[0]
                        if bin_file is not None]
            bin_list = [os.path.abspath(os.path.join(self.bin_path, bin_file))
                        for bin_file in bin_list]
        except LookupError:
            return None, (404, "Maybe the dataset does not exists")

        res = self.execute_insertion(delete_query, dataset_id)
        if res.rowcount == 1:
            res.close()
            print(bin_list)
            return bin_list, None
        else:
            res.close()
            return None, (404, "Some of your variables are not correct")

    def set_task(self, dataset_id, task_id):
        """Saves on database the task assigned to a dataset

        :param int dataset_id: The id of the dataset
        :param int task_id: The last task assigned to a dataset
        """
        # Substract to the model_path the relative bin_path
        query = "UPDATE dataset SET task=? WHERE id=? ;"
        res = self.execute_insertion(query, int(task_id), dataset_id)

        if res.rowcount == 1:
            res.close()
            return True, None
        else:
            res.close()
            return False, (400, "Failed when trying to save dataset on db")
