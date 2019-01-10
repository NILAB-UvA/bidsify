docker run --rm kaczmarj/neurodocker:0.4.3 generate docker \
           --base debian:stretch --pkg-manager apt \
           --install git \
           --fsl version=5.0.10 \
           --miniconda create_env=neuro \
                       conda_install="python=3.6 numpy pandas" \
                       pip_install="nibabel joblib pyyaml git+https://github.com/spinoza-rec/bidsify.git@master git+https://github.com/poldracklab/pydeface.git@master" \
                       activate=true \
           --workdir /home/neuro \
           --dcm2niix version=master  method=source \
           --entrypoint "/neurodocker/startup.sh bidsify" > Dockerfile

