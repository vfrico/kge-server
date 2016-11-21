#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding:utf-8
#
# data_access_base.py: Some basic classes for DAO and DTO
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
import copy
import kgeserver.server as server
import kgeserver.dataset as dataset
import kgeserver.wikidata_dataset as wikidata_dataset


def _CONFIG_get_dataset_path():
    try:
        return os.environ["DATASETS_PATH"]
    except KeyError:
        return "../datasets/"


def _CONFIG_get_sqlite_database():
    try:
        return os.environ["SQLITE_DATABASE_FILE_PATH"]
    except KeyError:
        return "server.db"


class MainDAO():
    def __init__(self):
        "Comprueba si existe la base de datos y/o la inicializa"

        self.database_file = _CONFIG_get_sqlite_database()

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
        self.bin_path = _CONFIG_get_dataset_path()
        if not os.path.exists(self.bin_path):
            print("The path {} does not exist, creating".format(self.bin_path))
            os.makedirs(self.bin_path)
        elif not os.access(self.bin_path, os.W_OK):
            msg = "The path {} is not writable".format(self.bin_path)
            print(msg)
            raise PermissionError(msg)

        self.connection = sqlite3.connect(self.database_file)

    def build_basic_db(self):

        self.execute_query("CREATE TABLE algorithm "
                           "(id INTEGER UNIQUE PRIMARY KEY, "
                           "embedding_size INTEGER, "
                           "max_epochs INTEGER, "
                           "margin FLOAT) ; ")

        self.execute_query("CREATE TABLE dataset "
                           "(id INTEGER UNIQUE PRIMARY KEY, "
                           "binary_dataset TEXT, "
                           "name TEXT, "
                           "binary_model TEXT, "
                           "binary_index TEXT,"
                           "algorithm INTEGER, "
                           "entities INTEGER, "
                           "relations INTEGER, "
                           "triples INTEGER, "
                           "status INTEGER, "
                           "FOREIGN KEY(algorithm) REFERENCES algorithm(id)"
                           ");")

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


class DTOClass():
    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return json.dumps(self.__dict__)

    def to_dict(self):
        dictionary = copy.copy(self.__dict__)
        for key in self.__dict__:
            if key[0] == "_":
                dictionary.pop(key)
        return dictionary
