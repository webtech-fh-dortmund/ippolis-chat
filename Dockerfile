FROM python:3.9-slim-bookworm

RUN apt-get update && \
    export DEBIAN_FRONTEND=noninteractive && \
    apt-get -y upgrade && \
    apt-get -y install \
        tini 

RUN pip install -U \
        pip 
#        setuptools \
#        wheel

WORKDIR /project

# Add a new system user with a home directory and grant ownership of the directory
RUN useradd -m -r user && \
    chown user /project

COPY requirements.txt ./
RUN pip install -r requirements.txt

# Define an ARG variable to be passed by the docker-compose.yml file (dynamically depending on the hosts environmental variable)
ARG running_locally
ARG system_port
ARG exposed_port
# which is then used as an environmental variable
ENV LLM_BOT_RUNNING_LOCALLY=$running_locally
RUN echo "Set LLM_BOT_RUNNING_LOCALLY to: $LLM_BOT_RUNNING_LOCALLY"
ENV SYSTEM_PORT=$system_port
ENV EXPOSED_PORT=$exposed_port

# Set the IP-addresses to be used if the system is run locally or remotely
ENV LOCAL_ADDRESS="http://127.0.0.1"
ENV REMOTE_ADDRESS="http://172.22.160.12"
ENV OLLAMA_IP="http://172.22.160.12:11434"

EXPOSE $system_port

COPY . .

USER user

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD python app.py
