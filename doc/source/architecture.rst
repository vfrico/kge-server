.. _architecture:


Service Architecture
====================

The service has an architecture based in docker containers. Currently it uses
three different containers:


- **Web container**: This container exposes the only open port of all system.
  Provides a ``gunicorn`` web server that accepts HTTP requests to the REST API
  and responds to them.

- **Celery Container**: This container is running on the background waiting for
  a task on its queue. It contains all library code and ``celery``.

- **Redis container**: The redis key-value storage is a dependency from Celery.
  It also stores all the progress of the tasks running on Celery queue.


Server deployment
-----------------

The old version of this repository didn't had any Dockerfile or image available
to run the code. This has changed, and two containers has been created to hold
both web server and asyncronous task daemon (celery).

Also, a simple container orchestation with docker-compose has been used. You can
see all the information inside images/ folder. It contains two Dockerfiles and
a docker-compose.yml that allows to build instantly the two images and connect
the containers. To run them you only have to clone the entire repository and
execute those commands:

::

    cd images/
    docker-compose build
    docker-compose up

The previous method is still available if you can't use docker-compose on your
machine


Images used
```````````
The previous image used on developement environment was ``recognai/jupyter-scipy-kge``.
This image contains a lot of code that the library and rest service does not use.

Using ``continuumio/miniconda3`` docker image as base, it is possible to install
only the required packages, minimizing the overall size of the container.

Both containers will launch a script on startup that will reinstall the kge-server
package on python path, to get latest developement version running, and then
will launch the service itself: gunicorn or celery worker.

Standalone containers to use in production are not still available.

Filesystem permissions
``````````````````````
The images used creates a new user called `kgeserver` with 1001 as its UID and
owns to the users group. This is helpful for a user running in development
environment. But the docker-compose file mounts some folders from host machine
that can create some ``PermissionError`` exceptions. To avoid them, always use
write permissions for users group. You are also
**free to modify the Dockerfile to solve the UID issues** you could have
inside your system.

The ``docker-compose`` command will create inside both celery and web containers
a data volume which is mounted on the root of the github repository.

Ports
`````
Currently, while development is taking place, the port which is being used is
**6789**, but you can change this easily on the ``docker_compose.yml`` file.


How to build documentation
``````````````````````````
This documentation page is built using sphinx framework, and is written in
reStructuredText. To build some documentation strings, it needs to have
some ``python`` libraries installed like ``numpy`` or ``scikit-learn``. It
exists one image to build this docs automatically, just running a docker container

::

    cd images/sphinx-doc
    docker build -t sphinx-doc .
    docker run -rm -v $PWD/../..:/home/kgeserver/kge-server sphinx-doc html

You may noticed the last argument called ``html``. It is the argument that will
be passed to the make argument. In this case, calling to html will lead to a
new ``doc/build/html`` folder with all new generated docs.
