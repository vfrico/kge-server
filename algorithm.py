#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding:utf-8
#
# Model class: create and train a model
# Copyright (C) 2016 Víctor Fernández Rico <vfrico@gmail.com>
# Copyright (C) 2016 Maximilian Nickel <mnick@mit.edu>
#
#   The original project is located in GitHub:
#   <https://github.com/mnick/holographic-embeddings/>
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

import numpy as np
import dataset
import skge
import experiment
import itertools
import threading


class TransEEval(experiment.FilteredRankingEval):

    def prepare(self, mdl, p):
        self.ER = mdl.E + mdl.R[p]

    def scores_o(self, mdl, s, p):
        return -np.sum(np.abs(self.ER[s] - mdl.E), axis=1)

    def scores_s(self, mdl, o, p):
        return -np.sum(np.abs(self.ER - mdl.E[o]), axis=1)


class HolEEval(experiment.FilteredRankingEval):

    def prepare(self, mdl, p):
        self.ER = ccorr(mdl.R[p], mdl.E)

    def scores_o(self, mdl, s, p):
        return np.dot(self.ER, mdl.E[s])

    def scores_s(self, mdl, o, p):
        return np.dot(mdl.E, self.ER[o])


class ModelTrainer(experiment.Experiment):
    """Creates a Model from a dataset and trains it"""

    def __init__(self, dataset, ncomp=150, afs='sigmoid',
                 trainer_type=skge.PairwiseStochasticTrainer,
                 model_type=skge.TransE, eval_type=TransEEval, **kwargs):
        """Constructor method.

        :param Dataset dataset: The dataset to train
        :param int ncomp: Number of latent components
        :param str afs: Activation function
        :param skge.Trainer trainer_type: The class desired for the trainer
        :param skge.Model model_type: The Model used to train
        :param Class eval_type: The class used to evaluate the model
        :param float margin: Margin for loss function
        :param str init: Initialization method
        :param float lr: Learning rate
        :param int max_epochs: Maximum number of epochs
        :param int ne: Number of negative examples
        :param int nbatches: Number of batches
        :param str fout: Path to store model and results TODO->CHANGE
        :param str fin: Path to imput data TODO->CHANGE
        :param int test_all: Evaluate the modell after x epochs
        :param bool no_pairwise: If true, trainer used is no pairwise
        :param str mode:
        :param str sampler:
        """
        super(ModelTrainer, self).__init__(dataset, **kwargs)
        self.ncomp = ncomp
        self.evaluator = eval_type
        self.trainer_type = trainer_type
        self.model_type = model_type
        self.afs = afs
        print(self.__dict__)

    def setup_trainer(self, size, sampler):
        """Configures a model and a trainer to be used in train method

        :param tuple size: A tuple (X, Y, Z) with the size of tensor
        :param skge.Sampler sampler: A sampler used by trainer.
        :return: An instantiated trainer
        :rtype: skge.Trainer
        """
        model = self.model_type(size, self.ncomp, init=self.init, rparam=0,
                                af=skge.activation_functions[self.afs])
        trainer = self.trainer_type(
            model,
            nbatches=self.nb,
            margin=self.margin,
            max_epochs=self.me,
            learning_rate=self.lr,
            samplef=sampler.sample,
            post_epoch=[self.callback]
        )
        return trainer


class Algorithm():
    """Generate several models to test and choose the right one
    """
    def __init__(self, dataset, thread_limiter=8):
        self.dataset = dataset
        self.th_semaphore = threading.Semaphore(thread_limiter)

    def find_best(self, margins=[0.2, 2.0], ncomps=range(50, 170, 20),
                  model_types=[skge.HolE, skge.TransE]):
        """Find the best training params for a given dataset

        This method makes several trains with different models and
        parameters, and returns a ModelTrainer Instance.
        :param list margins: A list of all margins to try
        :param list ncomps: A list of latent components
        :param list model_types: A list of models
        """
        threads = []
        model_trainer_list = []
        for tup in itertools.product(margins, ncomps, model_types):

            modtr = ModelTrainer(self.dataset, model_type=tup[2], max_epochs=50,
                                 margin=tup[0], ncomp=tup[1])
            model_trainer_list.append(modtr)

        def callbk_fn(modeltrainer):
            self.th_semaphore.release()
            print("Un model trainer ha terminado")
            # Extract evaluation data
            tuples = [(e['score'], e['epoch']) for e in modeltrainer.scores]
            for t in sorted(tuples, key=lambda t: t[0], reverse=True):
                modeltrainer.best_epoch = t[1]

            print(modeltrainer.__dict__)

        for mt in model_trainer_list:
            self.th_semaphore.acquire()
            t = threading.Thread(
                target=mt.thread_start,
                args=(callbk_fn, ))
            threads.append(t)
            t.start()

        for th in threads:
            th.join()

        return kwargs_dict

if __name__ == '__main__':

    dtset = dataset.Dataset()
    # dataset.load_from_binary("holographic-embeddings/data/wn18.bin")
    dtset.load_from_binary("wdata_15k.bin")

    alg = Algorithm(dtset)
    alg.find_best()
    # modeltrainer = ModelTrainer(dtset, model_type=skge.HolE, test_all=10,
    #                             max_epochs=200, margin=0.2, ncomp=50,
    #                             mode="rank")
    # modeltrained = modeltrainer.run()
    # print(modeltrainer.scores)
