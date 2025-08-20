
import json
import os
from os import getenv
from info_gpt.chat.lecture_knowledge_base import knowledge_base_from_json_files, get_json_util
from info_gpt.chat.ollama_rag import RAG, load_model_into_memory
from info_gpt.chat.knowledge_base import Knowledge_Base
import info_gpt.chat.web_tech_util as web_tech_util
    

import info_gpt.chat.lv_util as lv_util
import urllib.request

# The chatbots whose app configs will be loaded, should be set to ["*"] to load all. The FB4-Bot will be loaded always.
# New bots have to be added here and below as new app configs
enabled_bots = ["Datenbanken", "Dokumente", "Case_1", "Case_2", "Case_3", "Case_4", "analyse_gebrauchtwagen", "analyse_immobilien", "analyse_kardiologie", "analyse_musik", "Web"]

enabled_bots = ["Web"]
# enabled_bots = ["*"]

# The main config file, also used for the FB4-Chatbot
# Should be subclassed for the use with other chatbots
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
        self.log_dir = 'logs/fb4'#'logs'
        
        # The time between messages after which a user is deemed highly active
        self.high_activity_threshold_s = 5
        # The time a user has to wait additionally, if he is deemed highly active
        self.high_activity_waiting_penalty_s = 1

        
        self.knowledge_base_dir = 'knowledge_bases/fb4'#'knowledge_base_fb4'
        self.excluded_knowledge_base_files = []

        self.enable_rag = True
        # Choose the amount of best matching chunks to find for RAG
        # Default 10
        self.best_rag_matches = 10
        self.answer_only_with_metadata = False
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

        self.chat_system_prompt = ("Du bist Info-GPT, ein hilfreicher Assistent für Studierende am FB Informatik der FH Dortmund. Du kannst Fragen rund um das Studium beantworten."+
                        "Benutze ausschließlich die folgenden Informationen, um Fragen zu beantworten. "+
                        "Wenn eine Frage nicht mit Hilfe der vorliegenden Informationen beantwortet werden kann, dann sag nur, dass du die Frage nicht beantworten kannst:")
        # self.chat_system_prompt = "Du bist Info-GPT, ein hilfreicher Assistent für Studierende an der Fachhochschule Dortmund. Du kannst Fragen rund um das Studium beantworten."
        # self.chat_system_prompt = ("Dein Name ist Info-GPT, ein hilfreicher Assistent für Studierende am FB Informatik der Fachhochschule Dortmund. Du kannst Fragen rund um das Studium beantworten."+
        #                 "Benutze ausschließlich die folgenden Informationen, um Fragen zu beantworten:")

        self.root_website = "index_fb4_bot.html"

        # Load the environmental variable for the IP-address for the ollama-server
        # Strip any leading or trailing ", since they are added depending on the host-system and can lead to exceptions, when concatening strings (e.g. the ollama IP)
        self.ollama_ip = getenv('OLLAMA_IP').strip("\"")

        self.model = "llama3:8b-instruct-q8_0"
        # self.model = "llama3.1:8b-instruct-q8_0"

        # Check if the ollama_ip is truly available or if not, then use a fallback address
        def check_website_status(url):
            try:
                if urllib.request.urlopen(url).getcode() == 200:
                    load_model_into_memory(self)
                    return True
                raise Exception(f"{url} not available. Using fallback Ollama address.")
            except Exception as e:
                print(f"Error: {e} {url}")
            return False
        if not(check_website_status(self.ollama_ip)):
            self.ollama_ip = "http://172.22.160.12:11434"

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

class App_Config_Web(App_Config):
    def __init__(self) -> None:
        super().__init__()

        # Is used by RAG to determine if custom logic for this bot should be used
        self.chatbot_id = "Webster"

        # Add this config to the main config
        app_config.bot_configs[self.chatbot_id] = self

        self.log_dir = 'logs/web'

        self.knowledge_base_dir = 'knowledge_bases/web'
        self.load_knowledge_base_on_startup = False
        # self.knowledge_base = knowledge_base_from_json_files(self, self.knowledge_base_dir, rebuild=False)

        self.custom_metadata = web_tech_util.custom_metadata
        self.custom_post_RAG = web_tech_util.custom_post_RAG
        self.custom_pre_RAG = web_tech_util.custom_pre_RAG
        self.on_stop = web_tech_util.on_stop
        self.log_metadata = web_tech_util.log_metadata
        self.knowledge_base = web_tech_util.create_knowledge_base(self)

        self.enable_stundenplan_crawler = False
        self.enable_topic_detection = False
        self.load_model_on_startup = False
        self.load_knowledge_base_on_startup = False

        self.context_length = 4

        self.chat_system_prompt = ("Du bist Webster, ein hilfreicher Assistent für Studierende der Veranstaltung Web-Technologien am FB Informatik der FH Dortmund. Du kannst Fragen rund um die Veranstaltung beantworten. "+
                                "Du nimmst Feedback zu dir gerne an. "+
                                "Benutze ausschließlich die folgenden Informationen, um Fragen zu beantworten. ")

        self.root_website = "index_web_bot.html"

if "Web" in enabled_bots or "*" in enabled_bots:
    App_Config_Web()

class App_Config_Fallstudien(App_Config):
    def __init__(self) -> None:
        super().__init__()

        # Is used by RAG to determine if custom logic for this bot should be used
        self.chatbot_id = "Fallstudien-Bot"

        # Add this config to the main config
        app_config.bot_configs[self.chatbot_id] = self

        self.log_dir = 'logs/fallstudien'

        self.knowledge_base_dir = 'knowledge_bases/fallstudien'
        self.load_knowledge_base_on_startup = False
        self.knowledge_base = knowledge_base_from_json_files(self, self.knowledge_base_dir, rebuild=False)

        self.custom_metadata = lv_util.custom_metadata

        self.log_metadata = lv_util.log_metadata

        self.enable_stundenplan_crawler = False
        self.enable_topic_detection = False

        self.context_length = 4
        self.best_rag_matches = 5

        self.chat_system_prompt = ("Du bist Fallstudien-Bot, ein hilfreicher Assistent für Studierende der Veranstaltung Fallstudien am FB Wirtschaft der FH Dortmund. Du kannst Fragen rund um die Veranstaltung beantworten. "+
                "Benutze ausschließlich die folgenden Informationen, um Fragen zu beantworten. "+
                "Wenn eine Frage nicht mit Hilfe der vorliegenden Informationen beantwortet werden kann, dann sag nur, dass du die Frage nicht beantworten kannst:")

        self.root_website = "index_fallstudien_bot.html"

if "Fallstudien" in enabled_bots or "*" in enabled_bots:
    App_Config_Fallstudien()

class App_Config_Fallstudien_Diskussion(App_Config):
    def __init__(self) -> None:
        super().__init__()

        # Is used by RAG to determine if custom logic for this bot should be used
        self.chatbot_id = "Fallstudien_Diskussion-Bot"

        # Add this config to the main config
        app_config.bot_configs[self.chatbot_id] = self

        self.log_dir = 'logs/fallstudien_diskussion'

        self.knowledge_base_dir = 'knowledge_bases/fallstudien'
        self.load_knowledge_base_on_startup = False
        self.knowledge_base = knowledge_base_from_json_files(self, self.knowledge_base_dir, rebuild=False)

        def custom_metadata(user_query, app_config, knowledge_base, metadata):
            return metadata
        self.custom_metadata = custom_metadata

        self.enable_stundenplan_crawler = False
        self.enable_topic_detection = False

        self.context_length = 4
        self.best_rag_matches = 3

        self.chat_system_prompt = ("Du bist Fallstudien-Bot, ein Diskussions-Partner für Studierende der Veranstaltung Fallstudien am FB Wirtschaft der FH Dortmund. Du stellst gerne weiterführende Fragen am Ende deiner Aussagen, um deine Aussagen kritisch zu betrachten. "+
                "Nutze die folgenden Informationen als Basis der Diskussion: ")

        self.root_website = "index_fallstudien_diskussion_bot.html"

if "Fallstudien_Diskussion" in enabled_bots or "*" in enabled_bots:
    App_Config_Fallstudien_Diskussion()

class App_Config_Projektmanagement_A(App_Config):
    def __init__(self) -> None:
        super().__init__()

        # Is used by RAG to determine if custom logic for this bot should be used
        self.chatbot_id = "PM-Bot_A"

        # Add this config to the main config
        app_config.bot_configs[self.chatbot_id] = self

        self.log_dir = 'logs/projektmanagement_a'

        self.knowledge_base_dir = 'knowledge_bases/projektmanagement_a'
        self.load_knowledge_base_on_startup = False
        self.knowledge_base = knowledge_base_from_json_files(self, self.knowledge_base_dir, rebuild=False)

        self.custom_metadata = lv_util.custom_metadata

        self.log_metadata = lv_util.log_metadata

        self.enable_stundenplan_crawler = False
        self.enable_topic_detection = False

        self.context_length = 4

        self.chat_system_prompt = ("Du bist PM-Bot, ein hilfreicher Assistent für Studierende der Veranstaltung Projektmanagement am FB Wirtschaft der FH Dortmund. Du kannst Fragen rund um die Veranstaltung beantworten. "+
                "Benutze ausschließlich die folgenden Informationen, um Fragen zu beantworten. "+
                "Wenn eine Frage nicht mit Hilfe der vorliegenden Informationen beantwortet werden kann, dann sag nur, dass du die Frage nicht beantworten kannst:")

        self.root_website = "index_projektmanagement_a_bot.html"

if "Projektmanagement_A" in enabled_bots or "*" in enabled_bots:
    App_Config_Projektmanagement_A()

class App_Config_Projektmanagement_D(App_Config):
    def __init__(self) -> None:
        super().__init__()

        # Is used by RAG to determine if custom logic for this bot should be used
        self.chatbot_id = "PM-Bot_D"

        # Add this config to the main config
        app_config.bot_configs[self.chatbot_id] = self

        self.log_dir = 'logs/projektmanagement_d'

        self.knowledge_base_dir = 'knowledge_bases/projektmanagement_d'
        self.load_knowledge_base_on_startup = False
        self.knowledge_base = knowledge_base_from_json_files(self, self.knowledge_base_dir, rebuild=False)

        self.custom_metadata = lv_util.custom_metadata

        self.log_metadata = lv_util.log_metadata

        self.enable_stundenplan_crawler = False
        self.enable_topic_detection = False

        self.context_length = 4

        self.chat_system_prompt = ("Du bist PM-Bot, ein hilfreicher Assistent für Studierende der Veranstaltung Projektmanagement am FB Informatik der FH Dortmund. Du kannst Fragen rund um die Veranstaltung beantworten. "+
                "Benutze ausschließlich die folgenden Informationen, um Fragen zu beantworten. "+
                "Wenn eine Frage nicht mit Hilfe der vorliegenden Informationen beantwortet werden kann, dann sag nur, dass du die Frage nicht beantworten kannst:")

        self.root_website = "index_projektmanagement_d_bot.html"

if "Projektmanagement_D" in enabled_bots or "*" in enabled_bots:
    App_Config_Projektmanagement_D()

class App_Config_WI2(App_Config):
    def __init__(self) -> None:
        super().__init__()

        # Is used by RAG to determine if custom logic for this bot should be used
        self.chatbot_id = "WI2-Bot"

        # Add this config to the main config
        app_config.bot_configs[self.chatbot_id] = self

        self.log_dir = 'logs/wi_2'

        self.knowledge_base_dir = 'knowledge_bases/wi_2'
        self.load_knowledge_base_on_startup = False
        self.knowledge_base = knowledge_base_from_json_files(self, self.knowledge_base_dir, rebuild=False)

        self.custom_metadata = lv_util.custom_metadata

        self.log_metadata = lv_util.log_metadata

        self.enable_stundenplan_crawler = False
        self.enable_topic_detection = False

        self.context_length = 4

        self.chat_system_prompt = ("Du bist WI2-Bot, ein hilfreicher Assistent für Studierende der Veranstaltung Standardsoftware am FB Wirtschaft der FH Dortmund. Du kannst Fragen rund um die Veranstaltung beantworten. "+
                "Benutze ausschließlich die folgenden Informationen, um Fragen zu beantworten. "+
                "Wenn eine Frage nicht mit Hilfe der vorliegenden Informationen beantwortet werden kann, dann sag nur, dass du die Frage nicht beantworten kannst:")

        self.root_website = "index_wi_2_bot.html"

if "Standardsoftware" in enabled_bots or "*" in enabled_bots:
    App_Config_WI2()

class App_Config_DB_Bot(App_Config):
    def __init__(self) -> None:
        super().__init__()

        # Is used by RAG to determine if custom logic for this bot should be used
        self.chatbot_id = "DB-Bot"

        # Add this config to the main config
        app_config.bot_configs[self.chatbot_id] = self

        self.log_dir = 'logs/datenbanken'

        self.knowledge_base_dir = 'knowledge_bases/datenbanken'
        mapping_file = "videos.json"
        self.excluded_knowledge_base_files = [mapping_file]
        self.load_knowledge_base_on_startup = False
        self.knowledge_base = knowledge_base_from_json_files(self, self.knowledge_base_dir, rebuild=False)

        # Read the mapping file and create a connection between each mapping and each corresponding lecture/video
        json_util = get_json_util()
        lecture_video_id_mapping = {}
        mapping_js = json_util.read_json_file(self.knowledge_base_dir+"/"+mapping_file)
        for mapping in mapping_js:
            mapping["name"] = "none"
            lecture_video_id_mapping[mapping["id"]] = mapping
        kb_files = json_util.files_in_dir(self.knowledge_base_dir, filetype_filter=[".json"])
        for file in kb_files:
            # Skip the mapping file
            if file.endswith("/"+mapping_file):
                continue
            js = json_util.read_json_file(file)
            # Connect each mapping and each corresponding lecture/video
            for lecture in js:
                if lecture["video_id"] in lecture_video_id_mapping:
                    lecture_video_id_mapping[lecture["video_id"]]["name"] = lecture["name"]
                else:
                    print(f"No matching ID: {lecture['video_id']}")

        def custom_metadata(user_query, app_config, knowledge_base, metadata):
            metadata = lv_util.custom_metadata(user_query, app_config, knowledge_base, metadata, matches_to_find=10, final_matches=10)

            for entry in metadata:
                # Find the matching id
                mapping = [f for f in filter(lambda m: m["name"] == entry["Vorlesung"], lecture_video_id_mapping.values())]
                if len(mapping) == 1:
                    # Overwrite the attributes with the mapping's values
                    entry["url"] = mapping[0]["video_link"]
                    entry["Vorlesung"] = mapping[0]["video_name"]
                else:
                    entry["url"] = "URL not set."

            # Only keep videos of different lectures - e.g. combine all the ones from the same one
            metadata_copy = []
            for md in metadata:
                if not(any(md != md3 and md["Vorlesung"] == md3["Vorlesung"] for md3 in metadata_copy)):
                    metadata_copy.append(md)
            metadata = metadata_copy

            # Overwrite the ordering of the videos, by sorting them based on the semantic distance of the videotitles to the user's query
            raw = [entry["Vorlesung"] for entry in metadata]
            best_matches = lv_util.best_matches(user_query, app_config, knowledge_base, knowledge_base.embedder.encoder_model.encode(raw))
            metadata = [metadata[bm[0]] for bm in best_matches]

            # Reduce the number of links to 3
            metadata = metadata[0:3]

            return metadata

        self.custom_metadata = custom_metadata

        self.log_metadata = lv_util.log_metadata

        self.enable_stundenplan_crawler = False
        self.enable_topic_detection = False

        self.context_length = 4

        self.chat_system_prompt = ("Du bist DB-Bot, ein hilfreicher Assistent für Studierende der Veranstaltung Datenbanken am FB Informatik der FH Dortmund. Du kannst Fragen rund um die Veranstaltung beantworten. "+
                "Benutze ausschließlich die folgenden Informationen, um Fragen zu beantworten. "+
                "Wenn eine Frage nicht mit Hilfe der vorliegenden Informationen beantwortet werden kann, dann sag nur, dass du die Frage nicht beantworten kannst:")

        self.root_website = "index_db_bot.html"

if "Datenbanken" in enabled_bots or "*" in enabled_bots:
    App_Config_DB_Bot()

class App_Config_Doc_Bot(App_Config):
    def __init__(self) -> None:
        super().__init__()

        # Is used by RAG to determine if custom logic for this bot should be used
        self.chatbot_id = "Doc-Bot"

        # Add this config to the main config
        app_config.bot_configs[self.chatbot_id] = self

        self.log_dir = 'logs/doc-bot'

        self.knowledge_base_dir = 'knowledge_bases/doc'
        self.load_knowledge_base_on_startup = True
        self.knowledge_base = Knowledge_Base(self, self.chatbot_id)
        
        # Differ between url and text - only use the text for embeddings
        chunks = [{"content": emb["source"].split("\n")[1]} for article in self.knowledge_base.all_embeddings for emb in article["embeddings"] ]
        embeddings = self.knowledge_base.embedder.embed_chunks(chunks)
        i = 0
        for emb in self.knowledge_base.all_embeddings:
            emb["embedding"] = embeddings[i]
            i = i +1

        self.best_rag_matches = 10

        def custom_metadata(user_query, app_config, knowledge_base, metadata):

            # Embed the user's question
            question_embedding = knowledge_base.embedder.embed_user_query(user_query)

            # Always find a fixed number of matches via KNN and reduce the number later via a Reranker
            matches_to_find = self.best_rag_matches

            # Perform KNN search to find the best matches
            # Index, source_text, topic, distance
            best_matches = RAG().knn_search(question_embedding, knowledge_base.all_embeddings, min(matches_to_find, len(knowledge_base.all_embeddings[0]["embeddings"])))
            

            sources = [item['source'] for article in knowledge_base.all_embeddings for item in article['embeddings']]

            # Differ between url and text
            sources = [source.split("\n") for source in sources]

            # [{source, distance}]
            # best_matches = [{"source": sources[best_matches[i][0]], "distance": best_matches[i][3]} for i in range(len(best_matches))]
            # [{source, text, distance}]
            best_matches = [{"source": sources[best_matches[i][0]][0], "text": sources[best_matches[i][0]][1], "distance": best_matches[i][3]} for i in range(len(best_matches))]

            # Now sort based on source. This will be the secondary sort, e.g. first on KNN distance, then on source
            best_matches.sort(key=lambda match: match["source"], reverse=False)
            # Sort the best matches based on distance (ascending). This will be the secondary sort.
            best_matches.sort(key=lambda match: match["distance"], reverse=False)

            metadata = [{"source": bm["source"], "text": bm["text"], "distance": bm["distance"]} for bm in best_matches]

            return metadata

        self.custom_metadata = custom_metadata

        self.enable_stundenplan_crawler = False
        self.enable_topic_detection = False
        self.load_model_on_startup = False

        self.answer_only_with_metadata = True

        self.context_length = 1

        self.chat_system_prompt = ("")

        self.root_website = "index_doc_bot.html"

if "Dokumente" in enabled_bots or "*" in enabled_bots:
    App_Config_Doc_Bot()

class App_Config_Bib_Bot(App_Config):
    def __init__(self) -> None:
        super().__init__()

        # Is used by RAG to determine if custom logic for this bot should be used
        self.chatbot_id = "Bibbot"

        # Add this config to the main config
        app_config.bot_configs[self.chatbot_id] = self

        self.log_dir = 'logs/bibliothek'

        self.knowledge_base_dir = 'knowledge_bases/bibliothek'
        self.load_knowledge_base_on_startup = True
        self.knowledge_base = Knowledge_Base(self, self.chatbot_id)

        self.enable_stundenplan_crawler = False
        self.enable_topic_detection = False

        self.best_rag_matches = 13

        self.context_length = 3

        self.chat_system_prompt = ("Du bist Bibbot, ein hilfreicher Assistent für Fragen zur Bibliothek der FH Dortmund. "+
                "Benutze ausschließlich die folgenden Informationen, um Fragen zu beantworten. "+
                "Wenn eine Frage nicht mit Hilfe der vorliegenden Informationen beantwortet werden kann, dann sag nur, dass du die Frage nicht beantworten kannst:")

        self.root_website = "index_bib_bot.html"

if "Bibliothek" in enabled_bots or "*" in enabled_bots:
    App_Config_Bib_Bot()

class App_Config_Case_1_Bot(App_Config):
    def __init__(self) -> None:
        super().__init__()

        # Is used by RAG to determine if custom logic for this bot should be used
        self.chatbot_id = "Case_1"

        # Add this config to the main config
        app_config.bot_configs[self.chatbot_id] = self

        self.log_dir = 'logs/case_1'

        self.knowledge_base_dir = 'knowledge_bases/case_1'
        self.load_knowledge_base_on_startup = True
        self.knowledge_base = Knowledge_Base(self, self.chatbot_id)

        self.enable_stundenplan_crawler = False
        self.enable_topic_detection = False

        self.best_rag_matches = 10

        self.context_length = -1

        self.chat_system_prompt = ("Du bist Ralf Radgeber, Automobilkaufmann mit Schwerpunkt Fahrzeugtechnik vom Gebrauchtwagenhändler AutoSpezial GmbH. Dein Ziel ist es die Fragen eures Data Scientists zu beantworten. Gib keine konkreten Zahlen aus. Sei immer freundlich und antworte sachlich und professionell. Wenn eine Frage unklar ist oder wenn dir noch Informationen fehlen, dann frag nach. Wenn du eine Frage nicht beantworten kannst, dann gib es zu. Benutze für deine Antworten die folgenden Informationen: Die Daten wurden am 01.10.2025 aus unserem Produktivsystem gezogen. Der Datensatz beinhaltet alle Fahrzeuge die wir im vergangen Jahr verkauft haben. Somit spiegelt der Datensatz die Vorlieben unserer Kunden wieder und welche Verkaufspreise wir wirklich erzielt haben. Der Datensatz beinhaltet folgendende Spalten: Prop1_K, Prop2_F, Prop3_T, Prop4_P, Prop5_C, Prop6_A, Prop7_S. Leider kann unser System nur mit diesen kryptischen Spaltennamen arbeiten, daher folgt nun die entsprechende Beschreibung inkl. Ausprägungen und Einheiten: Prop1_K: Kilometerstand der Fahrzeuge zum Zeitpunkt des Verkaufs, numerischer Wert in Kilometer. Prop2_F: Treibstoffart die das Fahrzeug benötigt, kategorischer Wert mit Ausprägungen: D für Diesel, E für Elektrisch, B für Benzin. Prop3_T: Typ bzw. Karosserieform des Fahrzeuges, kategorischer Wert mit Ausprägungen K für Kombi und L für Limousine. Prop4_P: Leistung des Fahrzeuges in PS, numerischer Wert in PS. Prop5_C: Zustand des Fahrzeuges, kategorischer Wert mit Ausprägungen N für Normal, S für Schlecht und G für Gut. Prop6_A: Alter des Fahrzeuges in Jahre zum Zeitpunkt des Verkaufs, numerischer Wert in Jahren. Prop7_S: Verkaufspreis des Fahrzeuges in Euro, numerischer Wert in Euro.")

        self.root_website = "index_case_1_bot.html"

if "Case_1" in enabled_bots or "*" in enabled_bots:
    App_Config_Case_1_Bot()

class App_Config_Case_2_Bot(App_Config):
    def __init__(self) -> None:
        super().__init__()

        # Is used by RAG to determine if custom logic for this bot should be used
        self.chatbot_id = "Case_2"

        # Add this config to the main config
        app_config.bot_configs[self.chatbot_id] = self

        self.log_dir = 'logs/case_2'

        self.knowledge_base_dir = 'knowledge_bases/case_2'
        self.load_knowledge_base_on_startup = True
        self.knowledge_base = Knowledge_Base(self, self.chatbot_id)

        self.enable_stundenplan_crawler = False
        self.enable_topic_detection = False

        self.best_rag_matches = 10

        self.context_length = -1

        self.chat_system_prompt = ("Du bist Ralf Radgeber, Automobilkaufmann mit Schwerpunkt Fahrzeugtechnik vom Gebrauchtwagenhändler AutoSpezial GmbH. Dein Ziel ist es die Fragen eures Data Scientists zu beantworten. Sei immer freundlich und antworte sachlich und professionell. Wenn eine Frage unklar ist oder wenn dir noch Informationen fehlen, dann frag nach. Wenn du eine Frage nicht beantworten kannst, dann gib es zu. Benutze für deine Antworten die folgenden Informationen:")

        self.root_website = "index_case_2_bot.html"

if "Case_2" in enabled_bots or "*" in enabled_bots:
    App_Config_Case_2_Bot()

class App_Config_Case_3_Bot(App_Config):
    def __init__(self) -> None:
        super().__init__()

        # Is used by RAG to determine if custom logic for this bot should be used
        self.chatbot_id = "Case_3"

        # Add this config to the main config
        app_config.bot_configs[self.chatbot_id] = self

        self.log_dir = 'logs/case_3'

        self.knowledge_base_dir = 'knowledge_bases/case_3'
        self.load_knowledge_base_on_startup = True
        self.knowledge_base = Knowledge_Base(self, self.chatbot_id)

        self.enable_stundenplan_crawler = False
        self.enable_topic_detection = False

        self.best_rag_matches = 10

        self.context_length = -1

        self.chat_system_prompt = ("Du bist Ralf Radgeber, Automobilkaufmann mit Schwerpunkt Fahrzeugtechnik vom Gebrauchtwagenhändler AutoSpezial GmbH. Dein Ziel ist es die Fragen eures Data Scientists zu beantworten. Sei immer freundlich und antworte sachlich und professionell. Wenn eine Frage unklar ist oder wenn dir noch Informationen fehlen, dann frag nach. Wenn du eine Frage nicht beantworten kannst, dann gib es zu. Benutze für deine Antworten die folgenden Informationen:")

        self.root_website = "index_case_3_bot.html"

if "Case_3" in enabled_bots or "*" in enabled_bots:
    App_Config_Case_3_Bot()

class App_Config_Case_4_Bot(App_Config):
    def __init__(self) -> None:
        super().__init__()

        # Is used by RAG to determine if custom logic for this bot should be used
        self.chatbot_id = "Case_4"

        # Add this config to the main config
        app_config.bot_configs[self.chatbot_id] = self

        self.log_dir = 'logs/case_4'

        self.knowledge_base_dir = 'knowledge_bases/case_4'
        self.load_knowledge_base_on_startup = True
        self.knowledge_base = Knowledge_Base(self, self.chatbot_id)

        self.enable_stundenplan_crawler = False
        self.enable_topic_detection = False

        self.best_rag_matches = 10

        self.context_length = -1

        self.chat_system_prompt = ("Du bist Daniela Datenberg, Statistik-Expertin des Gebrauchtwagenhändlers AutoSpezial GmbH. Dein Ziel ist es die Fragen eures Data Scientists zu beantworten. Sei immer freundlich und antworte sachlich und professionell. Gib keine konkreten Zahlen aus. Antworte in kurzen Sätzen und für Studienanfänger verständlich. Wenn eine Frage unklar ist oder wenn dir noch Informationen fehlen, dann frag nach. Wenn du eine Frage nicht beantworten kannst, dann gib es zu. Benutze für deine Antworten die folgenden Informationen:")

        self.root_website = "index_case_4_bot.html"

if "Case_4" in enabled_bots or "*" in enabled_bots:
    App_Config_Case_4_Bot()

class App_Config_analyse_gebrauchtwagen_Bot(App_Config):
    def __init__(self) -> None:
        super().__init__()

        # Is used by RAG to determine if custom logic for this bot should be used
        self.chatbot_id = "analyse_gebrauchtwagen_bot"

        # Add this config to the main config
        app_config.bot_configs[self.chatbot_id] = self

        self.log_dir = 'logs/analyse_gebrauchtwagen'

        self.knowledge_base_dir = 'knowledge_bases/analyse_gebrauchtwagen'
        self.load_knowledge_base_on_startup = True
        self.knowledge_base = Knowledge_Base(self, self.chatbot_id)

        self.enable_stundenplan_crawler = False
        self.enable_topic_detection = False

        self.best_rag_matches = 10

        self.context_length = -1

        self.chat_system_prompt = ("Du bist Dieter Wehowski, Leiter des Gebrauchtwagenzentrums Wehowski & Söhne. Du hast eine Datenanalyse beauftragt, um den potenziellen Verkaufspreis von Gebrauchtwagen besser vorhersagen zu können. Deine Aufgabe ist es, Rückfragen des Data Scientists zur Aufgabenstellung oder zu Begriffen aus der Autowelt zu beantworten. Verhalte dich freundlich, sachlich und professionell. Wenn dir Informationen fehlen, frag nach. Wenn du etwas nicht weißt, gib es offen zu – du bist Gebrauchtwagenhändler, kein Statistiker. Wenn eine Frage nicht mit Hilfe der vorliegenden Informationen beantwortet werden kann, dann sag nur, dass du die Frage nicht beantworten kannst:")

        self.root_website = "index_analyse_gebrauchtwagen_bot.html"

if "analyse_gebrauchtwagen" in enabled_bots or "*" in enabled_bots:
    App_Config_analyse_gebrauchtwagen_Bot()

class App_Config_analyse_immobilien_Bot(App_Config):
    def __init__(self) -> None:
        super().__init__()

        # Is used by RAG to determine if custom logic for this bot should be used
        self.chatbot_id = "analyse_immobilien_bot"

        # Add this config to the main config
        app_config.bot_configs[self.chatbot_id] = self

        self.log_dir = 'logs/analyse_immobilien'

        self.knowledge_base_dir = 'knowledge_bases/analyse_immobilien'
        self.load_knowledge_base_on_startup = True
        self.knowledge_base = Knowledge_Base(self, self.chatbot_id)

        self.enable_stundenplan_crawler = False
        self.enable_topic_detection = False

        self.best_rag_matches = 10

        self.context_length = -1

        self.chat_system_prompt = ("Du bist Omar Karim, Immobilienmakler mit langjähriger Erfahrung im Wohnungsmarkt. Du hast eine Datenanalyse beauftragt, um fundiertere Empfehlungen zu Mietpreisen geben zu können. Deine Aufgabe ist es, Rückfragen des Data Scientists zur Fallbeschreibung oder zu Begriffen aus der Immobilienwelt zu beantworten. Antworte sachlich, freundlich und praxisnah. Du bist kein Statistiker, sondern Praktiker mit Erfahrung. Wenn eine Frage unklar ist, bitte um eine kurze Erklärung. Wenn du etwas nicht weißt, gib es offen zu – lieber ehrlich als ausgedacht. Du bist hilfsbereit und unkompliziert, erklärst Dinge gern so, wie du es auch einem Kunden erklären würdest – verständlich, ehrlich und ohne Fachchinesisch. Wenn eine Frage nicht mit Hilfe der vorliegenden Informationen beantwortet werden kann, dann sag nur, dass du die Frage nicht beantworten kannst:")

        self.root_website = "index_analyse_immobilien_bot.html"

if "analyse_immobilien" in enabled_bots or "*" in enabled_bots:
    App_Config_analyse_immobilien_Bot()

class App_Config_analyse_kardiologie_Bot(App_Config):
    def __init__(self) -> None:
        super().__init__()

        # Is used by RAG to determine if custom logic for this bot should be used
        self.chatbot_id = "analyse_kardiologie_bot"

        # Add this config to the main config
        app_config.bot_configs[self.chatbot_id] = self

        self.log_dir = 'logs/analyse_kardiologie'

        self.knowledge_base_dir = 'knowledge_bases/analyse_kardiologie'
        self.load_knowledge_base_on_startup = True
        self.knowledge_base = Knowledge_Base(self, self.chatbot_id)

        self.enable_stundenplan_crawler = False
        self.enable_topic_detection = False

        self.best_rag_matches = 10

        self.context_length = -1

        self.chat_system_prompt = ("Du bist Dr. Anna Jacoby, Fachärztin für Allgemeinmedizin. Du hast eine Datenanalyse zur Blutdruckentwicklung deiner Patientinnen und Patienten beauftragt. Deine Aufgabe ist es, Rückfragen des Data Scientists zur medizinischen Bedeutung der Variablen oder zur Fallbeschreibung zu beantworten. Antworte ruhig, sachlich und kompetent. Verwende bevorzugt medizinische Fachbegriffe, wenn sie passend sind – z. B. Hypertonie, Adipositas, Nikotinkonsum, Lipidprofil. Wenn eine Frage zu statistisch oder mathematisch formuliert ist, sag offen, dass du keine Statistikexpertin bist. Wenn dir Informationen fehlen oder du keine belastbare Auskunft geben kannst, formuliere das klar und ehrlich. Wenn eine Frage nicht mit Hilfe der vorliegenden Informationen beantwortet werden kann, dann sag nur, dass du die Frage nicht beantworten kannst:")

        self.root_website = "index_analyse_kardiologie_bot.html"

if "analyse_kardiologie" in enabled_bots or "*" in enabled_bots:
    App_Config_analyse_kardiologie_Bot()

class App_Config_analyse_musik_Bot(App_Config):
    def __init__(self) -> None:
        super().__init__()

        # Is used by RAG to determine if custom logic for this bot should be used
        self.chatbot_id = "analyse_musik_bot"

        # Add this config to the main config
        app_config.bot_configs[self.chatbot_id] = self

        self.log_dir = 'logs/analyse_musik'

        self.knowledge_base_dir = 'knowledge_bases/analyse_musik'
        self.load_knowledge_base_on_startup = True
        self.knowledge_base = Knowledge_Base(self, self.chatbot_id)

        self.enable_stundenplan_crawler = False
        self.enable_topic_detection = False

        self.best_rag_matches = 10

        self.context_length = -1

        self.chat_system_prompt = ("Du bist Amina, Projektverantwortliche beim Musikverlag GMDo. Du hast eine Datenanalyse in Auftrag gegeben, um herauszufinden, was einen erfolgreichen Song ausmacht. Deine Aufgabe ist es, Rückfragen des Data Scientists zur Aufgabenstellung oder zu Musikbegriffen zu beantworten. Sei freundlich, offen und interessiert. Du kennst dich mit Musik, Genres und Plattformen aus, aber nicht mit Statistik. Wenn dir etwas unklar ist, frag gern zurück. Wenn du etwas nicht weißt, gib es offen zu. Wenn eine Frage nicht mit Hilfe der vorliegenden Informationen beantwortet werden kann, dann sag nur, dass du die Frage nicht beantworten kannst:")

        self.root_website = "index_analyse_musik_bot.html"

if "analyse_musik" in enabled_bots or "*" in enabled_bots:
    App_Config_analyse_musik_Bot()
