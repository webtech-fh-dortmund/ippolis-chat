
import json
from os import getenv

class App_Config():
    def __init__(self) -> None:

        self.debug = False
        self.testing_mode = False
        self.use_config_file = False

        # Dictionary of bot ID and App_Config mappings. Should be extended if multiple bots are used in the application.
        self.bot_configs = {"": self}

        # Determine if the bot is running locally or remote
        # len() > 2 is necessary, since depending on the host-system env. variables might be initialized not as "" but with system characters
        self.llm_bot_running_locally = bool(getenv('LLM_BOT_RUNNING_LOCALLY')) and len(getenv('LLM_BOT_RUNNING_LOCALLY')) > 2

        # Is set to False as a workaround of a permission bug, to run the system locally on docker (remotely is fine)
        # Or in simpler terms: if the system is running without docker or not locally
        if bool(getenv('RUNNING_WITHOUT_DOCKER')) or not(self.llm_bot_running_locally):
            self.file_system_usage = True
        else:
            self.file_system_usage = False

        # For testing only
        self.test_streaming_token_delay = 0.075 # in seconds
        self.test_msg_delay_multiplier = 0
        if self.llm_bot_running_locally:
            self.test_streaming_token_delay = 0.075 # in seconds - 0.05 is pretty balanced
            self.test_msg_delay_multiplier = 0
        self.test_dir = 'tests'
        self.log_dir = 'logs'
        
        # The time between messages after which a user is deemed highly active
        self.high_activity_threshold_s = 5
        # The time a user has to wait additionally, if he is deemed highly active
        self.high_activity_waiting_penalty_s = 1

        
        self.knowledge_base_dir = 'knowledge_base_fb4'

        self.enable_rag = True
        self.enable_topic_detection = True
        # Determines the maximum number of interactions between a user and llm that is kept. Older interactions are discarded.
        # e.g. 2 means 4 messages total (e.g. user, llm, user, llm)
        # May be inconsistent if the user stops the bot's answers midway
        # Use -1 for unlimited.
        self.context_length = -1

        self.custom_rag = None
        self.custom_pre_RAG = None
        self.custom_post_RAG = None
        self.custom_metadata = None
        self.on_stop = lambda : None
        self.log_metadata = lambda metadata : None
        # Temporary storage for various needs, e.g. variables for custom functions for RAG
        self.tmp_storage = {}
        
        self.enable_stundenplan_crawler = False

        self.load_model_on_startup = True
        self.load_knowledge_base_on_startup = True

        # Is used by RAG to determine if custom logic for this bot should be used
        self.chatbot_id = "Info-GPT"

        # self.chat_system_prompt = ("Du bist Info-GPT, ein hilfreicher Assistent für Studierende am FB Informatik der FH Dortmund. Du kannst Fragen rund um das Studium beantworten."+
        #                 "Benutze ausschließlich die folgenden Informationen, um Fragen zu beantworten. "+
        #                 "Wenn eine Frage nicht mit Hilfe der vorliegenden Informationen beantwortet werden kann, dann sag nur, dass du die Frage nicht beantworten kannst:")
        # self.chat_system_prompt = "Du bist Info-GPT, ein hilfreicher Assistent für Studierende an der Fachhochschule Dortmund. Du kannst Fragen rund um das Studium beantworten."
        self.chat_system_prompt = ("Dein Name ist Info-GPT, ein hilfreicher Assistent für Studierende am FB Informatik der Fachhochschule Dortmund. Du kannst Fragen rund um das Studium beantworten."+
                        "Benutze ausschließlich die folgenden Informationen, um Fragen zu beantworten:")

        self.root_website = "index.html"

        # Load the environmental variable for the IP-address for the ollama-server
        # Strip any leading or trailing ", since they are added depending on the host-system and can lead to exceptions, when concatening strings (e.g. the ollama IP)
        self.ollama_ip = getenv('OLLAMA_IP').strip("\"")

        self.model = "llama3:8b-instruct-q8_0"
        # self.model = "llama3.1:8b-instruct-q8_0"

        # Try and load the custom config file, if it exists
        if self.use_config_file:
            try:
                with open('config.json') as f:
                    json_obj = json.load(f)

                    if json_obj["chat_system_prompt"] != None and json_obj["chat_system_prompt"] != "":
                        self.chat_system_prompt = json_obj["chat_system_prompt"]

                    if json_obj["ollama_ip"] != None and json_obj["ollama_ip"] != "":
                        self.ollama_ip = json_obj["ollama_ip"]

                    if json_obj["model"] != None and json_obj["model"] != "":
                        self.model = json_obj["model"]
            except Exception:
                # It is fine if the file doesn't exist
                pass

        # Temporary while main server is down
        # self.ollama_ip = "http://192.168.0.253:11434"

        self.port = int(getenv('SYSTEM_PORT'))
        self.exposed_port = int(getenv('EXPOSED_PORT'))

        # Allow cors to socket.io of the deployed websites
        if self.llm_bot_running_locally:
            self.base_ip_address = getenv('LOCAL_ADDRESS')
            # port is for "python app.py" and exposed_port for local docker, so either way of local deployment can be used
            self.allowed_cors_origins = [f"{self.base_ip_address}:{self.port}", f"{self.base_ip_address}:{self.exposed_port}"]
        else:
            self.base_ip_address = getenv('REMOTE_ADDRESS')
            self.allowed_cors_origins = [f"{self.base_ip_address}:{self.exposed_port}"]

app_config = App_Config()