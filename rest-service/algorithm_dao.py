import os
import time
import sqlite3
import redis
import json
import kgeserver.server as server
import kgeserver.dataset as dataset
import kgeserver.wikidata_dataset as wikidata_dataset
import data_access_base


class AlgorithmDAO(data_access_base.MainDAO):
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
