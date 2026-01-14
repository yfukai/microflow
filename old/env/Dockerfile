FROM condaforge/mambaforge

# Copy the conda environment file
COPY conda_env.yaml /tmp/conda_env.yaml

# Create the mamba environment
RUN mamba env create -f /tmp/conda_env.yaml && \
    mamba clean -afy

RUN echo "source activate microflow" > ~/.bashrc
ENTRYPOINT ["conda","run","-n","microflow"]