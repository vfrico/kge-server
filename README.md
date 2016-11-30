# Knowledge Graphs Embedding server

## What are Knowledge Graphs?

There exists many knowledge databases nowadays, and they are growing very
quickly. Some of them are open and has a very broad domain, like [DBpedia](http://es.dbpedia.org/) or
[Wikidata](http://wikidata.org/), both based on the data present in the well known Wikipedia. Some
of them are based on very specific domains, like [datos.bne.es](http://datos.bne.es/), which stores
the information from Spanish National Library (*Biblioteca Nacional de España*)
in an open way.

Most of those knowledge databases can be seen as knowledge graphs, where facts
is stored as triples: *head*, *label* and *tail*. This information is usually
stored using semantic web tools, like RDF and can be queried through some
languages like SPARQL.

## What are Embeddings?

Embeddings are a way to represent all the relationships that exists on graphs,
and they are commonly represented as multidimensional arrays.
Those are useful to perform some machine learning tasks such as look for
similar entities. With some embeddings models you can also do some simple
algebraic operations with those arrays like adding them or substract and predict
new entities.

## What is this server

This server provides a vertical solution on the machine learning area. This
goes from the creation of datasets wich represents those knowledge graphs
to methods to perform queries such as look for similar entities given another.
In the middle, the libary provides training and indexing methods that allows
the query operations shown above.

## Extra features

The *vertical solution* depicted above is available as a Python library, so
you can do a `setup.py install` and that's all. But you can also deploy a
web service using **docker** that will do any of those operations through a
HTTP client. You can take a look to the documentation and discover all the
things you can do [here](https://vfrico.github.io/kge-server/).


# Credits
* Copyright (C) 2016 Maximilian Nickel <mnick@mit.edu>
  * **Knowledge Graphs Embeddings** <https://github.com/mnick/scikit-kge>.
    Scikit-kge is a Python library to compute embeddings of knowledge graphs. Published under MIT License

  * **Holographic embeddings of Knowledge Graphs** <https://github.com/mnick/holographic-embeddings>.
    Code experiments which uses scikit-kge library.
