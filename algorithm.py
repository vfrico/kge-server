#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding:utf-8
#
# Model class: create and train a model
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

import numpy as np
import dataset
import skge


class TransEEval(FilteredRankingEval):

    def prepare(self, mdl, p):
        self.ER = mdl.E + mdl.R[p]

    def scores_o(self, mdl, s, p):
        return -np.sum(np.abs(self.ER[s] - mdl.E), axis=1)

    def scores_s(self, mdl, o, p):
        return -np.sum(np.abs(self.ER - mdl.E[o]), axis=1)


class ExpTransE(Experiment):

    def __init__(self, dataset, margin=2.0, init='nunif', lr=0.1, max_epochs=500, ne=1,
                 nbatches=100, fout=None, fin=None, test_all=50,
                 no_pairwise=False, mode='rank', sampler='random-mode', ncomp=50):
        super(ExpTransE, self).__init__(dataset, margin=margin, init=init,
            lr=lr, max_epochs=max_epochs, ne=ne, nbatches=nbatches,
            fout=fout, fin=fin, test_all=test_all,
            no_pairwise=no_pairwise, mode=mode, sampler=sampler)
        self.ncomp = ncomp
        self.evaluator = TransEEval

    def setup_trainer(self, sz, sampler):
        model = TransE(sz, self.ncomp, init=self.init)
        trainer = PairwiseStochasticTrainer(
            model,
            nbatches=self.nb,
            margin=self.margin,
            max_epochs=self.me,
            learning_rate=self.lr,
            samplef=sampler.sample,
            post_epoch=[self.callback]
        )
        return trainer

if __name__ == '__main__':

    dataset = dataset.Dataset()
    dataset.load_from_binary("holographic-embeddings/data/wn18.bin")

    ExpTransE(dataset, test_all=-1, max_epochs=40).run()
