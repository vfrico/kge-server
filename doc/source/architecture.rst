.. _architecture:


Service Architecture
====================

The service has an architecture based in docker containers. Currently it uses
two different containers:

- **Service container**: This holds all the code for the application to run,
  as well as different servers:

  - **gunicorn**: Is a web server that runs the code needed to access to all HTTP
    methods.
  - **celery**: Is a server running as daemon that runs the code for the heaviest
    tasks.

- **Redis container**: To get celery correctly work with tasks, it is required to
  run a redis database.

Server Deployment
-----------------

To configure the service we will need to install docker in our machine. After
that we will start pulling containers or creating images, so you need a good
internet connection and at least ~6 GB of free disk space

Getting all needed images
`````````````````````````
We need first to create the image for the service container. Until the container
is uploaded somewhere you can download it, you can use the following Dockerfile.
Copy it into a new folder and call it `Dockerfile`

::

    FROM jupyter/scipy-notebook

    MAINTAINER Víctor Fernández Rico <vfrico@gmail.com>

    USER root

    # install scikit-kge from github
    RUN git clone https://github.com/vfrico/kge-server.git
    RUN pip3 install requests --upgrade
    RUN pip3 install setuptools
    RUN pip3 install nose
    RUN cd kge-server/ && python3 setup.py install
    RUN rm -rf kge-server/
    RUN apt-get update && apt-get install -y redis-server
    RUN service redis-server stop


Now to build the image, change to the directory where you saved your Dockerfile
and execute the following command. You can tweak the :v1 version to whatever you
want.

::

    docker build -t kgeservice:v1 .


The second image we need to use is Redis. Fortunately the public docker registry
already has this image, so we will use it:

::

    docker pull redis


Once we have all needed images we need to run them

Running the environment
```````````````````````

The redis container acts like a dependency for our service container, so we
will launch it before. With the following command we start running a container
called `myredis`.

::

    docker run --name myredis -d redis

After this, we will run the service container. This container still has several
packages installed on it, like jupyter notebook. It has many parameters you can
tweak as you want.

::

    docker run -d -p 14397:8888 -p 6789:8000 -e PASSWORD="password"\
    --link myredis:redis --name serviciokge\
    -v $PWD/kge-server:/home/jovyan/work\
    kgeservice:v1

If everythin went ok, we can see all running containers. We must see at least our
two containers, called `myredis` and `serviciokge`

::

    docker ps

Now we enter into our container:

::

    docker exec -it serviciokge /bin/bash

and we have to run `~/work/rest-service/servicestart.sh` to run gunicorn and
`~/work/rest-service/celerystart.sh` to run celery.

After this you will be able to access the http rest service through the port :6789
