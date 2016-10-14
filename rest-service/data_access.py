import os
import sqlite3
database_file = "server.db"


class MainDAO():
    def __init__(self, database_file="server.db"):
        "Comprueba si existe la base de datos y/o la inicializa"

        self.database_file = database_file

        # Create the file itself
        try:
            os.stat(self.database_file)
        except OSError:
            # File does not exist. Create
            f = open(self.database_file, "w+")
            f.close()
            self.build_basic_db()

    def build_basic_db(self):
        self.execute_query("CREATE TABLE dataset "
                           "(id integer UNIQUE PRIMARY KEY, "
                           "binary_dataset VARCHAR(256), "
                           "binary_model VARCHAR(256), "
                           "binary_index VARCHAR(256),"
                           "embedding_size INTEGER, status INTEGER)")

        self.execute_query("INSERT INTO dataset VALUES "
                           "(NULL, 'level3.bin', '', '', 100, 2)")

    def execute_query(self, query):
        conn = sqlite3.connect(self.database_file)
        c = conn.cursor()

        c.execute(query)
        for row in c:
            print(row)
        conn.commit()
        c.close()
        return c


class DatasetDAO(MainDAO):
    def __init__(self, database_file="server.db"):
        super(DatasetDAO, self).__init__(database_file=database_file)

    def get_dataset_by_id(self, dataset_id):
        query = "SELECT * FROM dataset WHERE id={0}".format(dataset_id)
        res = self.execute_query(query)
        print(res)
