
import logging
from sys import stdout as sys_stdout
from pathlib import Path
import os
import json

def files_in_dir(root_dir, filetype_filter=[]):
  paths = []
  for file in os.listdir(root_dir):
    # If either any filetype match
    for ft in filetype_filter:
       if file.endswith(ft):
          paths.append(root_dir+"/"+file)
    # Or if none are specified, then add the file
    if len(filetype_filter) == 0:
      paths.append(root_dir+"/"+file)
  return paths

def read_file(url):
    with open(url, encoding="utf-8") as f:
        lines = f.read()+"\n"
    return lines

class Logging_Manager():
   def __init__(self, app_config) -> None:
      self.app_config = app_config
      self.log_dir = app_config.log_dir
      self.loggers = {}

      root = logging.getLogger("Chatbot")
      root.setLevel(logging.DEBUG)

      # Print normal messages unformated to standard out
      handler = logging.StreamHandler(sys_stdout)
      handler.setLevel(logging.DEBUG)
      handler.setFormatter(logging.Formatter('%(name)s: %(message)s'))
      root.addHandler(handler)

      if app_config.file_system_usage:
         # But also print them formated to the logfile
         file_handler = logging.FileHandler(filename='logfile.log', encoding='utf-8')
         file_handler.setLevel(logging.DEBUG)
         file_handler.setFormatter(logging.Formatter('%(asctime)s ### %(name)s ### %(levelname)s ### %(message)s'))
         root.addHandler(file_handler)

      self.logger = root

      # Create the logs directory if it does not exist yet
      Path(os.curdir+"/logs").mkdir(exist_ok=True)
      Path(os.curdir+"/"+self.log_dir).mkdir(exist_ok=True)

   def info(self, session_id, message):
      if not(session_id in self.loggers):
         logger = logging.getLogger("Info_GPT_"+session_id)
         logger.setLevel(logging.DEBUG)

         if self.app_config.file_system_usage:
            file_handler = logging.FileHandler(filename=self.log_dir+'/logfile_'+session_id+'.log', encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter('%(asctime)s ### %(message)s'))
            logger.addHandler(file_handler)

         self.loggers[session_id] = logger
      session_logger = self.loggers[session_id]

      # Don't log newlines
      message = message.replace("\n", "")

      session_logger.info(message)

   def debug(self, message):
      self.logger.debug(message)

   def delete_logger(self, session_id):
      if "Info_GPT_"+session_id in logging.getLogger().manager.loggerDict:
         del logging.Logger.manager.loggerDict["Info_GPT_"+session_id]

   def exception(self, message):
      self.logger.error(message)

   def get_logs(self)-> list[{str, str}]:
      """
      Returns a list of {file: str, content: str} objects
      """
      all_logs = []

      logs = files_in_dir(self.log_dir)

      for log in logs:
         all_logs.append({"file": log, "content": read_file(log)})

      # Sort the logs ascending based on the date and time of the first interaction
      all_logs.sort(key=lambda obj: obj["content"], reverse=False)

      return all_logs
