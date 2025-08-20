
import os
from re import sub as regexp_replace
from embeddings import Chunker, Embedder

from datetime import datetime
import json
from numpy import array as np_array
import numpy as np

def files_in_dir(root_dir, filetype_filter=[]):
  paths = []
  dirs = [root_dir]
  while len(dirs) > 0:
    dir = dirs.pop(0)
    for file in os.listdir(dir):
        # Differ between directories and files
        if os.path.isdir(dir+"/"+file):
            dirs.append(dir+"/"+file)
        else:
            # If either any filetype match
            for ft in filetype_filter:
                if file.endswith(ft):
                    paths.append(dir+"/"+file)
                # Or if none are specified, then add the file
            if len(filetype_filter) == 0:
                paths.append(dir+"/"+file)
  return paths

def read_file(url):
    with open(url, encoding="utf-8") as f:
        lines = f.read()
    return lines

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

class Knowledge_Base():
    def __init__(self, app_config, botId) -> None:
      self.debug = False
      
      self.app_config = app_config
      self.botId = botId

      self.embedded_data_file = 'embedded_data_'+botId+'.json'
      self.all_embeddings_file = 'all_embeddings_'+botId+'.json'

      # [{'embeddings': {"source", "embedding", "sourcelength", "id", "topic"}}]
      self.all_embeddings = {}
      self.all_topics = set()

      self.chunker = Chunker()
      self.embedder = Embedder()

      if app_config.load_knowledge_base_on_startup:
        if not(self.app_config.file_system_usage):
            self.prepare_data()
        else:
            if app_config.llm_bot_running_locally:
                # If any of the necessary files don't exist, then create them
                if not(os.path.isfile(self.embedded_data_file) and os.path.isfile(self.all_embeddings_file)):
                    self.prepare_data()
                else:
                    # Otherwise read their content
                    with open(self.embedded_data_file) as f:
                        self.embedded_data = json.load(f)
                        # Decode the numpy arrays from json lists
                        for d in self.embedded_data:
                            d["embeddings"] = np.asarray(d["embeddings"])
                    with open(self.all_embeddings_file) as f:
                        self.all_embeddings = json.load(f)
                        # Decode the numpy arrays from json lists
                        for d in self.all_embeddings:
                            d["embeddings"] = np.asarray(d["embeddings"])
                    # For Testing
                    # Reload the data anyway, since they change if the embedding is changed for testing
                    self.prepare_data()
            else:
                if os.path.isfile(self.embedded_data_file):
                    os.remove(self.embedded_data_file)
                    print("Removed embedded_data.json")
                if os.path.isfile(self.all_embeddings_file):
                    os.remove(self.all_embeddings_file)
                    print("Removed all_embeddings.json")
                # If running remotely the data should always be created, since it is combersome to remove the files manually
                self.prepare_data()


    def read_common_topics(self, filepath):
        result = []
        with open(filepath, encoding="utf-8") as file:
            js = json.load(file)
            for knowledge_base in js:
                files = js[knowledge_base]
                result = result + [f"{knowledge_base}/{f}.txt" for f in files]
        return result

    def prepare_data(self):
        root_dir = self.app_config.knowledge_base_dir

        paths = files_in_dir(root_dir)

        if len(paths) == 0:
            raise Exception("Knowledge base is empty")
        
        # Handle shared topics from other chatbots
        for p in paths:
            if p.endswith("GemeinsameThemen.txt") or p.endswith("Gemeinsame Themen.txt"):
                # Don't keep the file
                paths.remove(p)
                # Add the files of the other chatbots
                common_topic_files = self.read_common_topics(p)
                paths = paths + common_topic_files

        if self.debug: print(f"Knowledge Base Paths: {paths}")

        # List of type: {"id": id, "filename": file, "topic": topic, "content": content}
        raw_data = self.read_files(paths, ["txt"])
        if self.debug: print(f"Knowledge Base raw data: {raw_data}")

        self.embedded_data, self.all_embeddings = self.prepare_raw_data(raw_data)

        if self.app_config.llm_bot_running_locally and self.app_config.file_system_usage:
            with open(self.embedded_data_file, 'w') as f:
                json.dump(self.embedded_data, f, cls=NumpyEncoder)
            with open(self.all_embeddings_file, 'w') as f:
                json.dump(self.all_embeddings, f, cls=NumpyEncoder)

    def prepare_raw_data(self, raw_data):       
        for f in raw_data:
            self.all_topics.add(f["topic"])

        meta_data = self.read_meta_data(raw_data)
        if self.debug: print(f"Knowledge Base meta data: {meta_data}")
        
        chunked_data = self.chunker.chunk(meta_data)
        if self.debug: print(f"Knowledge Base chunked data: {chunked_data}")

        chunked_data = self.remove_duplicate_chunks(chunked_data)

        print("Embedding started: "+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        embedded_data, all_embeddings = self.embedder.embed(chunked_data)
        print("Embedding done: "+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        if self.debug: print(f"Knowledge Base embedded_data: {len(embedded_data)}")
        if self.debug: print(f"Knowledge Base all_embeddings: {len(all_embeddings)}")

        # if self.debug: print(f"Knowledge Base chunked data: {embedded_data}")
        # if self.debug: print(f"Knowledge Base all_embeddings: {all_embeddings}")

        return embedded_data, all_embeddings

    def clear_data(self):
       # Clear the previous data of the kb
       self.embedded_data = []
       self.all_embeddings = []

    def extend_data(self, raw_data):
       # raw_data should be a list of type: {"id": id, "filename": file, "topic": topic, "content": content}
       embedded_data, all_embeddings = self.prepare_raw_data(raw_data)
       for e in embedded_data:
         self.embedded_data.append(e)
       for a in all_embeddings:
         self.all_embeddings.append(a)

    def jsonify_embeddings(self, data):
       for d in data:
          d["embeddings"] = d["embeddings"].tolist()

    def unjsonify_embeddings(self, data):
       for d in data:
          d["embeddings"] = np_array(d["embeddings"])

    def read_files(self, paths, filetype_filter=[]):
        files = []
        id = 0
        def add_file(file, id):
            # Read the filename (without ".") and use it as the topic
            topic = regexp_replace(r"(.*/)|\..*", "", file)
            content = read_file(file)
            files.append({"id": id, "filename": file, "topic": topic, "content": content})

        for file in paths:
            # Only read files whose filetypes match
            for ft in filetype_filter:
                if file.endswith(ft):
                    add_file(file, id)
                    id = id + 1
                    break
            # Or if none are specified
            if len(filetype_filter) == 0:
                add_file(file, id)
                id = id + 1

        return files

    def read_meta_data(self, raw_data):
       # TODO read meta data for each file/topic
       # either from 1 single meta_file or from the files directly
       # meta_data could be e.g. keywords, name/topic, pdf_files etc.

       return raw_data
    
    def remove_duplicate_chunks(self, chunked_data):
       
        # while self.remove_duplicates(chunked_data):
        #    pass

        return chunked_data
    
    def remove_duplicates(self, chunked_data):
        for c in chunked_data:
           id = c["id"]
           content = c["content"]
           print (f"c {content}")

           for d in chunked_data:
              
              if d["id"] != id and d["content"] == content:
                 chunked_data.remove(c)
                 
                 print(f"remove_duplicates(): {content}")

                 return True
        return False