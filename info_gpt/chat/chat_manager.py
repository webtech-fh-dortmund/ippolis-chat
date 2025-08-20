from datetime import datetime

import json
from threading import Thread
from time import sleep

from traceback import format_exc as traceback_format_exc

from ollama_rag import send_msg_ollama
from knowledge_base import Knowledge_Base

from logging_manager import Logging_Manager

from random import randint

# The maximum number of parallel requests, should match with Ollama's env. variable OLLAMA_NUM_PARALLEL
PARALLEL_REQUESTS = 20

class User():
   def __init__(self, session_id: any, chat_manager, bot_id) -> None:
     self.session_id = session_id
     self.knowledge_base = chat_manager.get_knowledge_base(bot_id)
     self.bot_id = bot_id
     self.bot_config = chat_manager.app_config.bot_configs[bot_id] if bot_id in chat_manager.app_config.bot_configs else chat_manager.app_config

     self.current_request = None
     self.stopped_streaming = False
     self.context = [[{}]]
     # Since the user has send no message yet, set the last_message_time far into the future
     self.last_message_time = datetime.max
     self.request_counter= 0
     self.language = "de"

   def __str__(self) -> str:
      return f"session_id: {self.session_id}, context: {self.context}, request_counter: {self.request_counter}"

class User_Manager():
   def __init__(self) -> None:
      self.users = []

   def create_user(self, session_id, chat_manager, bot_id):
      # Don't create a new user if it already exists
      for i, user in enumerate(self.users):
         if user.session_id == session_id:
            return user
      user = User(session_id, chat_manager, bot_id)
      self.users.append(user)
      return user

   def delete_user(self, session_id):
      for user in self.users:
         if user.session_id == session_id:
            self.users.remove(user)
            break

   def get_user(self, session_id) -> User:
      for u in self.users:
         if u.session_id == session_id:
            return u
      print(f"Exception: No user with session_id: {session_id}")
      return None
   
   def print_all_users(self):
      for i, user in enumerate(self.users):
         print(f"{user}")


user_manager = User_Manager()

class Request():
   def __init__(self, request_id: any, session_id: any) -> None:
      self.request_id = request_id
      self.session_id = session_id
      self.starttime = datetime.now()
      self.confirmation_time = self.starttime
      print(f"New Request: {session_id} {request_id}")

DUMMY_REQUEST = Request(-1, -1)

class Request_Reservation():
   def __init__(self, request: Request) -> None:
      self.request = request
      self.waiting = True
      self.ongoing = False

class Heartbeat():
   def __init__(self) -> None:
      pass

class Request_Thread(Thread):
    def __init__(self, possible_requests: int):
        Thread.__init__(self, daemon=True)
        self.possible_requests: int = possible_requests
        self.queued_requests: list[Request_Reservation] = []
        self.ongoing_requests: list[Request_Reservation] = []
        self.stopped_requests: list[int] = []

    def run(self):
        while True:
           sleep(0.01)
           
           for r in self.ongoing_requests:
              if not(r.ongoing):
                 self.ongoing_requests.remove(r)
                 break

           if len(self.queued_requests) > 0 and len(self.ongoing_requests) < self.possible_requests:
              request = self.queued_requests.pop(0)
              request.waiting = False
              request.ongoing = True
              self.ongoing_requests.append(request)
           
           if len(self.stopped_requests) > 0:
              request_id = self.stopped_requests.pop(0)
              request = self.get_request(request_id)
              if request in self.ongoing_requests:
                 request.ongoing = False
                 self.ongoing_requests.remove(request)
              if request in self.queued_requests:
                 request.waiting = False
                 self.queued_requests.remove(request)

    def get_request(self, request_id):
       for r in self.ongoing_requests:
          if r.request.request_id == request_id:
            return r
       for r in self.queued_requests:
          if r.request.request_id == request_id:
            return r
       print(f"get_request(): Can find request for id {request_id}")
      #  msg = f"get_request(): Can find request for id {request_id}"
      #  raise Exception(msg)
       return None

    def queue_request(self, request):
       self.queued_requests.append(request)

    def stop_request(self, request_id):
       self.stopped_requests.append(request_id)
   
request_thread = Request_Thread(PARALLEL_REQUESTS)
request_thread.start()

class Message_Handler():
   def __init__(self, app_config) -> None:
      pass
   
   def send_msg(self, data, botPerformance, user, reservation, knowledge_base, streaming):
      if user.bot_config.custom_rag == None:
         for d in send_msg_ollama(data, botPerformance, user.context, user.language, user.bot_config, reservation, user.knowledge_base, streaming):
            yield d
            # Delayed sending
            sleep(user.bot_config.test_streaming_token_delay)
      else:
         for d in user.bot_config.custom_rag(data, user.bot_config, user.knowledge_base):
            yield d
            # Delayed sending
            sleep(user.bot_config.test_streaming_token_delay)

class Chat_Manager():
    def __init__(self, app_config) -> None:
      self.app_config = app_config
      self.knowledge_bases = {}
      self.message_handler = Message_Handler(app_config)
      self.user_manager = User_Manager()
      self.logging_manager = Logging_Manager(app_config)
      self.logging_managers = {"": self.logging_manager}

    def send_os(self, data, session_id, bot_id=""):
       self.get_logging_manager(bot_id).info(session_id, f"Send OS: session_id: {session_id}, os: {data['os']}")

    def send_feedback(self, data, session_id, bot_id=""):
       self.get_logging_manager(bot_id).info(session_id, f"Send Feedback: session_id: {session_id}, request_id: {data['requestId']}, feedback: {data['feedback']}")
      #  TODO continue

    def is_overloaded(self, session_id="none"):
       # The system is overloaded if there are more than 80% of possible requests executed
       overload_threshold = request_thread.possible_requests * 0.8
       overloaded = len(request_thread.ongoing_requests) >= overload_threshold

       if overloaded:
          self.get_logging_manager().info(session_id, f"Overloaded: session_id: {session_id}, ongoing_requests: {len(request_thread.ongoing_requests)}/{overload_threshold}")

       return overloaded

    def getCurrentUserCount(self):
       return len(request_thread.ongoing_requests)

    def get_logging_manager(self, bot_id=""):
       if not(bot_id in self.logging_managers):
          self.logging_managers[bot_id] = Logging_Manager(self.get_bot_config(bot_id))
       return self.logging_managers[bot_id]

    def get_bot_config(self, botId):
       return self.app_config.bot_configs[botId] if botId in self.app_config.bot_configs else self.app_config

    def get_knowledge_base(self, botId):
       if botId == "":
          self.get_logging_manager(botId).debug(f"---botId ist not set. It should be set via Javascript in the bots' website.---")

       if not(botId in self.knowledge_bases):
          config = self.get_bot_config(botId)
          self.knowledge_bases[botId] = config.knowledge_base if hasattr(config, 'knowledge_base') else Knowledge_Base(config, botId)
       return self.knowledge_bases[botId]

    def stop_streaming(self, session_id, request_id):
       print(f"stop_streaming(): {session_id} {request_id}")

       user = user_manager.get_user(session_id)
       user.stopped_streaming = True

       if user.current_request != None:
          request_thread.stop_request(user.current_request.request_id)

          user.bot_config.on_stop()

          self.get_logging_manager(user.bot_id).info(session_id, f"Stopped request: session_id: {session_id}, request_id: {request_id}")

    def send_msg(self, data, botPerformance, session_id, streaming):
      user = user_manager.get_user(session_id)
      logging_manager = self.get_logging_manager(user.bot_id)

      logging_manager.info(session_id, f"New message: session_id: {session_id}, data: {data}")

      # If a request for the user is already ongoing, don't create a new one => message is discarded
      # => is ok, since this case should never happen => log
      if user.current_request != None:
         print(f"send_msg(): Exception: new request send, although one is still ongoing for session_id: {session_id}, data: {data}, request: {user.current_request.request_id}")
         yield("info", {"done": True, "data": "Exception: new request send, although one is still ongoing. The new request will be discarded.\n"})
         return

      # If the user has send a request recently, then add a few seconds of waiting time
      now = datetime.now()
      seconds_after_last_message = (now-user.last_message_time).seconds
      if seconds_after_last_message < user.bot_config.high_activity_threshold_s:
         print(f"user {user.session_id} has to wait longer due to high activity")
         # yield("info", {"done": True, "data": "Längere Wartezeit wegen hoher Aktivität.\n"})
         i = 0
         while i < user.bot_config.high_activity_waiting_penalty_s:
            sleep(0.1)
            i = i + 0.1

      print(f"seconds_after_last_message(session_id: {session_id}: {seconds_after_last_message} seconds)")

      if user.stopped_streaming:
         user.stopped_streaming = False
         # Enable the user's input again
         yield("request_done", {"done": True, "request_id":-1})
         return

      request = Request(user.request_counter, session_id)
      user.current_request = request
      user.request_counter = user.request_counter + 1

      reservation = Request_Reservation(request)
      request_thread.queue_request(reservation)

      logging_manager.info(session_id, f"Message queued: session_id: {session_id}, request_id: {request.request_id}")

      while reservation.waiting and not (user.stopped_streaming):
         sleep(0.01)

      # If the request or reservation has not been stopped meanwhile
      if reservation.ongoing and not (user.stopped_streaming):

         
         if user.bot_config.testing_mode:
            ########################
            ######For testing#######
            ########################
            # Wait x seconds
            waittime = randint(5, 10) * user.bot_config.test_msg_delay_multiplier
            # waittime = randint(2, 3)
            for i in range(0, waittime*10):
               if not(reservation.ongoing):
                  break
               sleep(0.1)
            ########################
            ########################
            ########################

         full_reply = ""

         # Then send the data
         user.last_message_time = datetime.now()
         try:
            for reply in self.message_handler.send_msg(data, botPerformance, user, reservation, user.knowledge_base, streaming):
               if not(reservation.ongoing):
                  break
               yield(('new_msg', {"done":reply[0], "request_id":request.request_id, "data":reply[1], "metadata":reply[2] if len(reply) > 2 else ""}))
               
               # Only log the metadata if it received and if a custom function can process it
               if len(reply) > 2:
                  metadata = user.bot_config.log_metadata(reply[2])
                  if metadata != None:
                     logging_manager.info(session_id, f"Metadata: session_id: {session_id}, request_id: {request.request_id}, data: {metadata}")

               full_reply = full_reply + reply[1]
         except Exception as err:
            print(err)
            print(traceback_format_exc())
            logging_manager.exception(f"Exception: {traceback_format_exc()}")

         reservation.ongoing = False

         logging_manager.info(session_id, f"Message reply: {full_reply}")

      logging_manager.info(session_id, f"Message done: session_id: {session_id}, request_id: {request.request_id}")

      yield("request_done", {"done": True, "request_id":request.request_id})

      print(f"request done: {session_id} {request.request_id}")

      logging_manager.delete_logger(session_id)

      user.current_request = None
      user.stopped_streaming = False
