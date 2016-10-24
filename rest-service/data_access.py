import os
import time
import sqlite3
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
            self.build_basic_db()

        # Path where all binary files have its relative path
        self.bin_path = "../"

    def build_basic_db(self):

        self.execute_query("CREATE TABLE algorithm "
                           "(id INTEGER UNIQUE PRIMARY KEY, "
                           "embedding_size INTEGER) ; ")

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

        default_datasets = [
                        {"id": 0, "binary_dataset": 'wikidata_25k.bin',
                         "binary_model": "",
                         "binary_index": 'wikidata_25k.annoy.bin',
                         "status": 2, 'algorithm': 0},
                        {"id": 1, "binary_dataset": '4levels.bin',
                         "binary_model": 'modelo_guardado.bin',
                         "binary_index": 'annoy_index_big.bin',
                         "status": 2, 'algorithm': 0},
                        {"id": 2, "binary_dataset": '4levels.bin',
                         "binary_model": 'modelo_guardado.bin',
                         "binary_index": 'annoyIndex.500.bin',
                         "status": 2, 'algorithm': 0}
                         ]
        default_algorithms = [
                        {"id": 0, "embedding_size": 100}
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
        conn = sqlite3.connect(self.database_file)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("PRAGMA foreign_keys = ON;")
        c.execute(query, args)
        row = c.fetchone()
        conn.commit()
        c.close()
        return row

    def execute_insertion(self, query):
        conn = sqlite3.connect(self.database_file)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("PRAGMA foreign_keys = ON;")
        c.execute(query)
        conn.commit()
        return c


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
        """Returns a dataset given its id

        :return: A dataset dictionary or none
        :rtype: tuple
        """
        query = "SELECT * FROM dataset WHERE id={0} ;".format(dataset_id)
        res = self.execute_query(query)
        # Query has return nothing
        if res is None:
            return None, (404, "Dataset {} not found".format(dataset_id))
        # Query has an object
        self.binary_dataset = res['binary_dataset']
        self.binary_model = res['binary_model']
        self.binary_index = res['binary_index']
        self.dataset['status'] = res['status']
        self.dataset['id'] = int(dataset_id)

        if res['triples'] and res['relations'] and res['entities']:
            # These fields are filled and can be readable
            self.dataset['triples'] = res['triples']
            self.dataset['entities'] = res['entities']
            self.dataset['relations'] = res['relations']
        else:
            # Fields should be readed from file
            dtst = dataset.Dataset()
            dtst.load_from_binary(self.bin_path+self.binary_dataset)
            self.dataset['triples'] = len(dtst.subs)
            self.dataset['entities'] = len(dtst.entities)
            self.dataset['relations'] = len(dtst.relations)

        alg_dao = AlgorithmDAO()
        algorithm, err = alg_dao.get_algorithm_by_id(res['algorithm'])
        if algorithm is None:
            return None, err
        self.dataset['algorithm'] = algorithm

        return (self.dataset, None)

    def build_dataset_object(self):
        dtst = dataset.Dataset()
        dtst.load_from_binary(self.bin_path+self.binary_dataset)
        return dtst

    def get_search_index(self):
        """Returns an instantiated search index from choosen dataset

        """
        if self.dataset['status'] < 2:
            return None, (409, "Dataset {id} has {status} status and is not "
                               "ready for search".format(**self.dataset))
        search_index = server.SearchIndex()
        search_index.load_from_file(self.bin_path + self.binary_index,
                                    self.dataset['algorithm']['embedding_size']
                                    )
        return search_index, None

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
        sql_sentence = ("INSERT INTO dataset VALUES "
                        "(NULL, '"+unique_name+"', '', '', 0, 0)")

        newdataset = datasetClass()
        newdataset.save_to_binary(self.bin_path+unique_name)

        result = self.execute_insertion(sql_sentence)
        rowid = result.lastrowid
        result.close()
        return rowid, None

    def get_all_datasets(self):
        """Queries the DB to retrieve all datasets

        :returns: A list of datasets objects
        :rtype: list
        """

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


class AlgorithmDAO(MainDAO):
    def __init__(self, database_file="server.db"):
        super(AlgorithmDAO, self).__init__(database_file=database_file)
        self.algorithm = {
            "embedding_size": None,
            "id": None
        }

    def get_algorithm_by_id(self, algorithm_id):
        query = "SELECT * FROM algorithm WHERE id=?"
        res = self.execute_query(query, algorithm_id)

        if res is None:
            return None, (404, "Algorithm "+str(algorithm_id)+" not found")
        self.algorithm['embedding_size'] = res['embedding_size']
        self.algorithm['id'] = res['id']
        return self.algorithm, None
