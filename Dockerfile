FROM ubuntu:trusty
MAINTAINER <lukassnoek@gmail.com>

COPY docker/files/neurodebian.gpg /root/.neurodebian.gpg

RUN apt-get update && apt-get upgrade -y && \
	apt-get install -y build-essential pkg-config cmake git pigz && \
	apt-get clean -y && apt-get autoclean -y && apt-get autoremove -y

RUN curl -sSL http://neuro.debian.net/lists/xenial.us-ca.full >> /etc/apt/sources.list.d/neurodebian.sources.list && \
    apt-key add /root/.neurodebian.gpg && \
    (apt-key adv --refresh-keys --keyserver hkp://ha.pool.sks-keyservers.net 0xA5D32F012649A5A9 || true)

# Installing Neurodebian packages (FSL, git)
  RUN apt-get update  && \
      apt-get install -y --no-install-recommends \
                      fsl-core \
                      fsl-mni152-templates && \
      apt-get install -y dcm2niix

ENV FSLDIR=/usr/share/fsl/5.0 \
    FSLOUTPUTTYPE=NIFTI_GZ \
    FSLMULTIFILEQUIT=TRUE \
    POSSUMDIR=/usr/share/fsl/5.0 \
    LD_LIBRARY_PATH=/usr/lib/fsl/5.0:$LD_LIBRARY_PATH \
    FSLTCLSH=/usr/bin/tclsh \
    FSLWISH=/usr/bin/wish \
    PATH=/usr/lib/fsl/5.0:/usr/lib/afni/bin:$PATH

# Installing and setting up miniconda
RUN curl -sSLO https://repo.continuum.io/miniconda/Miniconda3-4.3.11-Linux-x86_64.sh && \
    bash Miniconda3-4.3.11-Linux-x86_64.sh -b -p /usr/local/miniconda && \
    rm Miniconda3-4.3.11-Linux-x86_64.sh

ENV PATH=/usr/local/miniconda/bin:$PATH \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Installing precomputed python packages
RUN conda install -c numpy \
                     pandas \
                     joblib && \
    chmod -R a+rX /usr/local/miniconda && \
    chmod +x /usr/local/miniconda/bin/* && \
    conda clean --all -y

# Clone Github repo here and install BidsConverter
