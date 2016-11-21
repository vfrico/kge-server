FROM jupyter/scipy-notebook

MAINTAINER Víctor Fernández Rico <vfrico@gmail.com>

USER root

# install scikit-kge from github
#RUN git clone https://github.com/vfrico/scikit-kge.git
RUN pip3 install requests --upgrade
RUN pip3 install setuptools
RUN pip3 install nose
RUN git clone https://github.com/vfrico/kge-server.git && cd kge-server/ && python3 setup.py install
# RUN apt-get update && apt-get install -y redis-server
# RUN service redis-server stop

ENTRYPOINT ["tini", "--"]
CMD ["/bin/bash", "launch_services_celery.sh"]

COPY launch_services_celery.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/launch_services_celery.sh

# Switch back to jovyan to avoid accidental container runs as root
# USER $NB_USER
