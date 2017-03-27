FROM continuumio/miniconda3:4.2.12

MAINTAINER Víctor Fernández <vfrico@gmail.com>

USER root

# Install some dependencies and updates
RUN apt-get update && \
    apt-get install -y gcc g++ && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Add user for run server
ENV CONDA_USER_UID 1001
ENV CONDA_USER kgeserver
RUN useradd -m -s /bin/bash -N -u $CONDA_USER_UID $CONDA_USER && \
    chown $CONDA_USER_UID:users -R /opt/conda

# Install some conda dependencies
RUN conda install --yes scikit-learn scipy cython &&\
    conda clean -tipsy

# Install kge-server and its dependencies
RUN pip install --upgrade pip
RUN pip install setuptools requests nose falcon
RUN cd /home/$CONDA_USER/ && git clone https://github.com/vfrico/kge-server.git && \
    cd kge-server/ && python3 setup.py install

# Once tools to build Annoy are used, uninstall them
RUN apt-get remove gcc g++ -y && \
    apt-get autoremove -y

# Init system and launch script
ENTRYPOINT ["tini", "--"]
CMD ["/bin/bash", "launch_gunicorn.sh"]

COPY launch_gunicorn.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/launch_gunicorn.sh

# Exit from root user
USER $CONDA_USER
ENV PATH /opt/conda/bin:$PATH
