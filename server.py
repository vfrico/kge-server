import sys
import os
import dataset
import algorithm
import skge
from annoy import AnnoyIndex


class Server():
    def __init__(self, search_index):
        """A server works with a SearchIndex.
        """
        if not search_index or search_index.index is None:
            print("The search index has not been generated")
            return None
        elif not search_index.ready:
            print("The search index must be built")
            return None
        else:
            self.index = search_index.index

    def similarity_by_id(self, id, k):
        """Given an entity id, return the k'th most similar entities

        :param int id: The entity id
        :param int k: The entities to show
        :returns: A list with k id's, which are the most similar entities
        :rtype: list
        """
        return self.index.get_nns_by_item(id, k)


class SearchIndex():
    def __init__(self):
        """Generates a new SearchIndex, used in Server Class

        The main purpose of this class is to generate an index, without
        the Server class needs to know the search index it is being used

        A search index is ready to be used when an index exists
        and it isready (when an index has been built).
        """
        self.index = None
        self.ready = False

    def build_from_trained_model(self, trained_model, depth):
        """Creates an index from a trained model

        :param TrainedModel trained_model: The trained model
        :param int depth: The depth desired to generate the search index
        """
        entities_matrix = trained_model.E
        nrows, emb_size = entities_matrix.shape

        self.index = AnnoyIndex(emb_size)

        # Populate the search index with the trained embedding
        for row in range(0, nrows):
            vector = list(entities_matrix[row])
            self.index.add_item(row, vector)

        # Generate the index itself. This may take long time
        self.index.build(depth)

        # Index ready
        self.ready = True

    def save_to_binary(self, filepath):
        if self.index is None or self.ready is False:
            print("The index is not ready to be saved")
            return False

        self.index.save(filepath)

    def load_from_file(self, filepath, emb_size):
        self.index = AnnoyIndex(emb_size)
        self.index.load(filepath)


if __name__ == '__main__':

    e_matrix = a.E
    nrows, nmod = e_matrix.shape

    t = AnnoyIndex(nmod)
    for i in range(0, nrows):
        v = list(e_matrix[i])
        t.add_item(i, v)

    t.build(1000)
    t.save('test.ann')
