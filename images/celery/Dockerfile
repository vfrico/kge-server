# FROM jupyter/scipy-notebook
FROM jupyter/minimal-notebook

MAINTAINER Víctor Fernández Rico <vfrico@gmail.com>

USER root

RUN apt-get update && \
    apt-get install -y --no-install-recommends libav-tools && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN conda install --yes \
    'pandas=0.19*' \
    'scipy=0.18*' \
    'scikit-learn=0.18*' \
    'cython=0.25*' \
    'numba=0.29*'
    # conda remove --quiet --yes --force qt pyqt && \
    # conda clean -tipsy

# install scikit-kge from github
#RUN git clone https://github.com/vfrico/scikit-kge.git
RUN pip install requests --upgrade
RUN pip install setuptools
RUN pip install nose
RUN git clone https://github.com/vfrico/kge-server.git && cd kge-server/ && python3 setup.py install
# RUN apt-get update && apt-get install -y redis-server
# RUN service redis-server stop

ENTRYPOINT ["tini", "--"]
CMD ["/bin/bash", "launch_services_celery.sh"]

COPY launch_services_celery.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/launch_services_celery.sh

# Switch back to jovyan to avoid accidental container runs as root
# USER $NB_USER
