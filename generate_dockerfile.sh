docker run --rm kaczmarj/neurodocker:0.4.3 generate docker \
           --base debian:stretch --pkg-manager apt \
           --install git \
           --fsl version=5.0.10 \
           --dcm2niix version=master method=source \
           --miniconda create_env=neuro \
                       conda_install="python=3.6 numpy pandas" \
                       pip_install="nipype git+https://github.com/poldracklab/pydeface.git@master pyyaml nibabel joblib" \
                       activate=true \
           --install gnupg2 \
           --run "curl --silent --location https://deb.nodesource.com/setup_10.x | bash -" \
           --install nodejs \
           --run "npm install -g bids-validator" \
           --copy . /home/neuro/bidsify \
           --run "pip install -e /home/neuro/bidsify" \
           --workdir /home/neuro \
           --volume /raw \
           --volume /bids > Dockerfile
