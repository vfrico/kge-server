# Knowledge Graphs Embedding server

## Try the webapp now

Thanks to [OEG-UPM](https://github.com/oeg-upm) there are a server available where you can
try out the webapp and the service itself.

* Webapp: http://wiener.dia.fi.upm.es:9393/
* Service: http://wiener.dia.fi.upm.es:6789/

## What are Knowledge Graphs?

There are many knowledge databases nowadays, and they are growing very
quickly. Some of them are open and have a very broad domain, like [DBpedia](http://es.dbpedia.org/) or
[Wikidata](http://wikidata.org/), both based in existent data on Wikipedia. Other knowledge databases
are based on very specific domains, like [datos.bne.es](http://datos.bne.es/), which stores
the information from Spanish National Library (*Biblioteca Nacional de España*)
in an open, machine readable, way.

Most of those knowledge databases can be seen as **knowledge graphs**, where facts
can be seen as triples: *head*, *label* and *tail*. This information is usually
stored using semantic web tools, like RDF and can be queried through some
languages like SPARQL.

## What are Embeddings?

Embeddings are a way to represent all the relationships that exists on graphs,
and they are commonly represented as multidimensional arrays.
Those are useful to perform some machine learning tasks such as look for
similar entities. With some embeddings models you can also do some simple
algebraic operations with those arrays like adding them or substract and predict
new entities.

## What is this server?

This server provides a vertical solution on the machine learning area,
going from the creation of datasets wich represents those knowledge graphs,
to methods to perform queries such as look for similar entities given another.
In the middle, the server provides training and indexing models that allows
the query operations shown above.

## What is included here?

The *vertical solution* depicted above is available as a Python library, so
you can do a `python3 setup.py install` and that's all. But you can also deploy a
web service using **docker** that is able to do almost every of those operations
through a HTTP client. You can take a look to the documentation and discover all the
things you can do [here](https://vfrico.github.io/kge-server/).

# Installation/Execution

You can use the Python library as is, or you can start a server, and use all
the endpoints available.

# Library installation

This repository provides a setuptools `setup.py` file to install the library
on your system. It is pretty easy. Simply make `sudo python3 setup.py install` and
it will install the library. Maybe some extra dependencies are required to run
into your system, if so, you can execute this to get them all installed:

    conda install scikit-learn scipy cython

And if you are using normal python3:

    pip3 install numpy scipy pandas sympy nose scikit-learn

But the recommended way to getthe REST service working is to execute into the
docker environment. You only need to have installed `docker` and `docker-compose`
in your system.

# Service execution

To run the service, go to images folder, execute `docker-compose up` and you
will have a server on the port `localhost:6789` ready to listen HTTP requests.

    cd images/
    docker-compose up -d
    curl http://localhost:6789/datasets

After this you will have an HTTP REST server listening to the API. but if you
want to run the python library alone, you can connect to any of the docker
containers created:

    docker exec -it images_web_1 /bin/bash

If you are experiencing troubles when executing the docker image, check your
user UID and change the user UID in **all** `Dockerfiles` inside `images/` folder.
Then rebuild the images with: `docker-compose build --no-cache`

See more instructions about deployment at the
[docs](https://vfrico.github.io/kge-server/architecture.html#server-deployment).

## Supported environment

The whole project has been built using Python 3.5 distributed by Anaconda,
inside a docker image. If you want to run the development environment, just
use this image `recognai/jupyter-scipy-kge`.

# External Libraries

Some of this work couldn't be possible without some of these libraries

* Maximilian Nickel [mnick@mit.edu](mailto:mnick@mit.edu)
  * [**Knowledge Graphs Embeddings**](https://github.com/mnick/scikit-kge).
    Scikit-kge is a Python library to compute embeddings of knowledge graphs. Published under MIT License

  * [**Holographic embeddings of Knowledge Graphs**](https://github.com/mnick/holographic-embeddings).
    Code experiments which uses scikit-kge library.

* [Spotify/Annoy](https://github.com/spotify/annoy)  Approximate Nearest Neighbors in C++/Python optimized for memory usage and loading/saving to disk

* [Celery](https://github.com/celery/celery/) is a Distributed Task Queue for Python.

* [Falcon](https://github.com/falconry/falcon) was used to build the API REST
