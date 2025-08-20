# Initialize environmental variables from a .env file, so all sub-modules can access them
from dotenv import load_dotenv
load_dotenv()

from gevent import monkey

# https://www.gevent.org/api/gevent.monkey.html
monkey.patch_all()

from info_gpt.chat.security.security import secure_app

from os import getenv
from flask_wrapper import Flask_Wrapper
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler

class App_Config():
    def __init__(self) -> None:

        self.debug = False

        # Determine if the bot is running locally or remote
        # len() > 2 is necessary, since depending on the host-system env. variables might be initialized not as "" but with system characters
        self.llm_bot_running_locally = bool(getenv('LLM_BOT_RUNNING_LOCALLY')) and len(getenv('LLM_BOT_RUNNING_LOCALLY')) > 2
        
        self.testing_environment = bool(getenv('TESTING_ENVIRONMENT')) and len(getenv('TESTING_ENVIRONMENT')) > 2

        self.running_without_docker = bool(getenv('RUNNING_WITHOUT_DOCKER')) and len(getenv('RUNNING_WITHOUT_DOCKER')) > 2

        if self.llm_bot_running_locally:
            self.base_ip_address = getenv('LOCAL_ADDRESS')
        else:
            self.base_ip_address = getenv('REMOTE_ADDRESS')

        self.port = int(getenv('SYSTEM_PORT'))
        self.exposed_port = int(getenv('EXPOSED_PORT'))

        # If running with docker the local port is mapped to an exposed port via docker,
        # if running locally without docker, the same port should be used
        if self.running_without_docker:
            self.exposed_port = self.port

app_config = App_Config()

if __name__ == '__main__':
    wrapper = Flask_Wrapper(app_config)
    app = wrapper.get_app()

    secure_app(app)

    http_server = WSGIServer(("0.0.0.0", app_config.port), app, handler_class=WebSocketHandler)
    http_server.serve_forever()