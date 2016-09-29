import sys
import os
import dataset
import algorithm
import skge
from annoy import AnnoyIndex


class Server():
    def __init__(self, trainedModel):
        """A server should be created with a trained model
        """
        self.matrix = trainedModel.E
        self.n_elements, self.ncomps = self.matrix.shape

        self.index = AnnoyIndex(self.ncomps)

        for n_row in range(0, self.n_elements):
            elem_vector = list(self.matrix[n_row])
            t.add_item(n_row, elem_vector)

    def build_index(self, depth, filepath):
        self.index.build(depth)
        self.index.save(filepath)


if __name__ == '__main__':

    e_matrix = a.E
    nrows, nmod = e_matrix.shape

    t = AnnoyIndex(nmod)
    for i in range(0, nrows):
        v = list(e_matrix[i])
        t.add_item(i, v)

    t.build(1000)
    t.save('test.ann')
