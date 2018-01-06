FROM neurodebian:xenial-non-free
MAINTAINER <lukassnoek@gmail.com>

# Installing Neurodebian packages (FSL, git)
RUN apt-get update  && \
    apt-get install -y --no-install-recommends \
                    curl \
                    ca-certificates \
                    build-essential \
                    fsl-core \
                    git \
                    dcm2niix

# Installing and setting up miniconda
RUN curl -sSLO https://repo.continuum.io/miniconda/Miniconda3-4.3.11-Linux-x86_64.sh && \
    bash Miniconda3-4.3.11-Linux-x86_64.sh -b -p /usr/local/miniconda && \
    rm Miniconda3-4.3.11-Linux-x86_64.sh

ENV PATH=/usr/local/miniconda/bin:$PATH \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Installing precomputed python packages
RUN conda install -y -c numpy \
                     pandas \
                     joblib && \
    chmod -R a+rX /usr/local/miniconda && \
    chmod +x /usr/local/miniconda/bin/* && \
    conda clean --all -y

RUN pip install nipype nibabel pyyaml

RUN git clone https://github.com/poldracklab/pydeface.git && \
        cd pydeface && \
        python setup.py install && \
        cd ..

# Clone Github repo here and install BidsConverter
RUN git clone -b refactor --single-branch https://github.com/lukassnoek/BidsConverter.git && \
    cd BidsConverter && \
    python setup.py install

ENTRYPOINT ["convert2bids"]
