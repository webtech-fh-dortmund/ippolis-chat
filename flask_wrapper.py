
from flask import Flask, send_from_directory, render_template
from flask import Flask, request, render_template, has_request_context, jsonify, redirect, send_from_directory
from flask_socketio import SocketIO, emit
from markupsafe import escape

import os
import urllib.request

from collections.abc import Iterable

from info_gpt.chat.chat_manager import Chat_Manager, user_manager
from info_gpt.chat.ollama_rag import load_model_into_memory
from app_configs import app_config as main_config

from flask_security import auth_required

class Flask_Wrapper():
    def __init__(self, app_config) -> None:
      self.app_config = app_config
      self.chat_manager = Chat_Manager(main_config)

    def get_app(self):
        app = Flask(__name__)
        socketio = SocketIO(app, cors_allowed_origins=main_config.allowed_cors_origins)
        self.socketio = socketio

        def get_session_id():
            sid = 0
            if has_request_context():
                if hasattr(request, 'sid'):
                    sid = request.sid
            print(f"get_session_id(): {sid}")
            return sid

        # The two main files for the deployed websites
        template = 'index.html'
        maintenance_html = 'maintenance.html'
        landing_page = 'landing.html'

        # Opional downtime parameter to be displayed on the maintenance page
        downtime = "" # "Estimated downtime from 19:00 until 20:00 o'clock"

        # Return a boolean indicating if the resource at the given url can be accessed
        def service_available(url):
            if url.startswith("http://127.0.0.1"):
                return True
            status_code = request_status_code(url)
            # The service is available if the status code is "200 ok"
            return status_code == 200
        def request_status_code(url):
            try:
                status_code = urllib.request.urlopen(url).getcode()
            except Exception as err:
                if type(err) == urllib.error.HTTPError:
                    return (False, err.code)
                print(f"Error: {err} - Service unavailable: {url}")
                return -1
            return status_code

        # Return a template for the given service with the given title
        # If the service is unavailable return the maintenance template
        def service_template(service_url, title):
            if not(service_available(service_url)):
                return render_template(maintenance_html, title=title, downtime=downtime)
            return render_template(template, src=service_url, title=title)

        # Combine the config's ip-address and port and add a subpath, if given
        def full_route(port_increment, subpath="", default_path=""):
            # Differ if the bot is running remotely with docker or not
            if not(self.app_config.llm_bot_running_locally) and not(self.app_config.running_without_docker) and default_path != "":
                return default_path+("" if len(subpath) == 0 else f"/{escape(subpath)}")
            else:
                # e.g. 127.0.0.1:5000/subpath
                return self.app_config.base_ip_address+f":{self.app_config.exposed_port+port_increment}"+("" if len(subpath) == 0 else f"/{escape(subpath)}")

        #
        # Setup the routing to the different sub-services
        #

        @app.route('/', defaults={'subpath': ""})
        def info_gpt(subpath):
            return render_template("index_fb4_bot.html", title="Info-GPT")

        @app.route('/web', defaults={'subpath': ""})
        def web_bot(subpath):
            return render_template("index_web_bot.html", title="Webster")

        @app.route('/fallstudien', defaults={'subpath': ""})
        def fallstudien_bot(subpath):
            return render_template("index_fallstudien_bot.html", title="Fallstudien-Bot")

        @app.route('/fallstudien_diskussion', defaults={'subpath': ""})
        def fallstudien_diskussion_bot(subpath):
            return render_template("index_fallstudien_diskussion_bot.html", title="Fallstudien-Bot")

        @app.route('/projektmanagement_wirtschaft', defaults={'subpath': ""})
        def projektmanagement_wirtschaft(subpath):
            return render_template("index_projektmanagement_a_bot.html", title="PM-Bot")

        @app.route('/projektmanagement_informatik', defaults={'subpath': ""})
        def projektmanagement_informatik(subpath):
            return render_template("index_projektmanagement_d_bot.html", title="PM-Bot")

        @app.route('/standardsoftware', defaults={'subpath': ""})
        def standardsoftware(subpath):
            return render_template("index_wi_2_bot.html", title="WI2-Bot")
        
        @app.route('/datenbanken', defaults={'subpath': ""})
        def datenbanken(subpath):
            return render_template("index_db_bot.html", title="DB-Bot")

        @app.route('/doc-bot', defaults={'subpath': ""})
        def doc_bot(subpath):
            return render_template("index_doc_bot.html", title="Doc-Bot")

        @app.route('/bibliothek', defaults={'subpath': ""})
        def bibliothek(subpath):
            return render_template("index_bib_bot.html", title="Bibbot")

        @app.route('/case_1', defaults={'subpath': ""})
        def case_1(subpath):
            return render_template("index_case_1_bot.html", title="Case")
        @app.route('/case_2', defaults={'subpath': ""})
        def case_2(subpath):
            return render_template("index_case_2_bot.html", title="Case")
        @app.route('/case_3', defaults={'subpath': ""})
        def case_3(subpath):
            return render_template("index_case_3_bot.html", title="Case")
        @app.route('/herr_radgeber', defaults={'subpath': ""})
        def herr_radgeber(subpath):
            return render_template("index_case_1_bot.html", title="Herr Radgeber")
        @app.route('/frau_datenberg', defaults={'subpath': ""})
        def frau_datenberg(subpath):
            return render_template("index_case_4_bot.html", title="Herr Datenberg")
        
        @app.route('/analyse_musik', defaults={'subpath': ""})
        def analyse_1(subpath):
            return render_template("index_analyse_musik_bot.html", title="IPPOLIS-Analyse")
        @app.route('/analyse_immobilien', defaults={'subpath': ""})
        def analyse_2(subpath):
            return render_template("index_analyse_immobilien_bot.html", title="IPPOLIS-Analyse")
        @app.route('/analyse_kardiologieanalyse', defaults={'subpath': ""})
        def analyse_3(subpath):
            return render_template("index_analyse_kardiologie_bot.html", title="IPPOLIS-Analyse")
        @app.route('/analyse_gebrauchtwagen', defaults={'subpath': ""})
        def analyse_4(subpath):
            return render_template("index_analyse_gebrauchtwagen_bot.html", title="IPPOLIS-Analyse")
        
        @app.route('/statistic', defaults={'subpath': ""})
        @app.route('/statistic/<path:subpath>')
        def statistic(subpath):
            return service_template(full_route(port_increment=1, subpath=subpath, default_path=""), "TP2-Bot")
        
        @app.route('/wirtschaft', defaults={'subpath': ""})
        @app.route('/wirtschaft/<path:subpath>')
        def wirtschaft(subpath):
            return service_template(full_route(port_increment=3, subpath=subpath, default_path=""), "FB9 Info-Bot")

        @app.route('/web', defaults={'subpath': ""})
        @app.route('/web/<path:subpath>')
        def web(subpath):
            return service_template(full_route(port_increment=4, subpath=subpath, default_path=""), "Web-Tech Bot")
        
        @app.route('/landing')
        def landing():
            return render_template(landing_page, title="IPPOLIS-Chat")
        
        # The icon to displayed in the browser's tab
        @app.route("/favicon.ico")
        def favicon():
            return send_from_directory(os.path.join(app.root_path, 'static'),
                            'favicon.ico', mimetype='image/vnd.microsoft.icon')
        

        @app.route("/getLogs/<bot_id>")
        @auth_required()
        def getLogs(bot_id):
            return jsonify(self.chat_manager.get_logging_manager(escape(bot_id)).get_logs())
        
        @app.route("/getCurrentUserCount")
        def getCurrentUserCount():
            return jsonify(self.chat_manager.getCurrentUserCount())
        
        @socketio.on('connect')
        def connect():
            session_id = get_session_id()
            # Inform the user that the system is almost overloaded
            if self.chat_manager.is_overloaded(session_id):
                emit("info", {"done":True, "data":"#overloaded"}, room=session_id)

        @socketio.on("stop_streaming")
        def stop_streaming(data):
            self.chat_manager.stop_streaming(get_session_id(), data["data"]["requestId"])

        @socketio.on("send_feedback")
        def send_feedback(data):
            print(f"send_feedback(): data: {data}")
            feedback = data["data"]
            
            id = get_session_id()
            # Either create a new user or use the existing one
            user = user_manager.create_user(id, self.chat_manager, data["botId"])

            self.chat_manager.send_feedback(feedback, get_session_id(), data["botId"])
            # Reply if the user send custom feedback
            if "customFeedback" in feedback:
                if user.language == "de":
                    emit("info", {"done":True, "data":"Danke für dein Feedback!"}, room=get_session_id())
                else:
                    emit("info", {"done":True, "data":"Thanks for your feedback!"}, room=get_session_id())

        @socketio.on("change_language")
        def change_language(data):
            id = get_session_id()
            # Either create a new user or use the existing one
            user = user_manager.create_user(id, self.chat_manager, data["botId"])
            user.language = data["data"]["language"]

        @socketio.on("send_msg")
        def send_msg(data):

            print(f"send_msg(): {data}")

            if (data["data"] == "CodeWord"):
                print("#####Enabled Dev-Mode#####")
            if (data["data"] == "EndCodeWord"):
                print("#####Disabled Dev-Mode#####")

            id = get_session_id()
            # Inform the user of his id
            emit("send_id", {"done": True, "data": id}, room=id)

            # Either create a new user or use the existing one
            user_manager.create_user(id, self.chat_manager, data["botId"])

            if "os" in data and len(data["os"]) > 0:
                self.chat_manager.send_os(data, id, data["botId"])

            # Inform the user that the system is almost overloaded
            if self.chat_manager.is_overloaded(id):
                emit("info", {"done":True, "data":"#overloaded"}, room=id)

            result = self.chat_manager.send_msg(data, data["botPerformance"], id, True)

            # Differ between streamed replies and single replies
            if isinstance(result, Iterable):
                print(f"send_msg() streamed reply")
                for r in result:
                    emit(r[0], r[1], room=id)
            else:
                print(f"send_msg() single reply")
                emit(result[0], result[1], room=id)

        if main_config.load_model_on_startup:
            load_model_into_memory(main_config)

        @socketio.on("set_best_rag_matches")
        def change_best_rag_matches(data):
            id = get_session_id()
            # Either create a new user or use the existing one
            user = user_manager.create_user(id, self.chat_manager, data["botId"])
            user.bot_config.best_rag_matches = int(data["best_rag_matches"])

        return app
