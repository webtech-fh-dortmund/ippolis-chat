
import util.json_util as json_util
from knowledge_base import Knowledge_Base

import json
import os
import numpy as np
from pathlib import Path

def get_json_util():
    return json_util

def knowledge_base_from_json_files(app_config, knowledge_base_dir, rebuild=True):
    lectures = []
    kb_files = json_util.files_in_dir(knowledge_base_dir, filetype_filter=[".json"])
    for file in kb_files:
        # Skip any excluded files
        if any(f == Path(file).stem+".json" for f in app_config.excluded_knowledge_base_files):
            continue
        js = json_util.read_json_file(file)
        for lecture in js:
            lectures.append(lecture)
    return Lecture_Knowledge_Base(app_config, app_config.chatbot_id, lectures, rebuild=rebuild)

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

class Lecture_Knowledge_Base(Knowledge_Base):
    def __init__(self, app_config, bot_id, lectures, categories=[], misc_category="", lecture_category=lambda lecture_name: lecture_name, rebuild=True) -> None:
        super().__init__(app_config, bot_id)

        all_embeddings_file = 'all_embeddings_'+bot_id+'.json'

        # If the knowledge base should be rebuild or if the file doesn't exist yet, then rebuild it
        if rebuild or not(os.path.isfile(all_embeddings_file)):
            self.all_embeddings = self.create_kb(lectures, categories, misc_category, lecture_category)

            # Save the embeddings as a file
            if self.app_config.llm_bot_running_locally and self.app_config.file_system_usage:
                with open(all_embeddings_file, 'w') as f:
                    json.dump(self.all_embeddings, f, cls=NumpyEncoder)
        else:
            # Else load the file
            with open(self.all_embeddings_file) as f:
                self.all_embeddings = json.load(f)
                # Decode the numpy arrays from json lists
                for d in self.all_embeddings:
                    d["embeddings"] = np.asarray(d["embeddings"])
        
    def create_kb(self, lectures, categories=[], misc_category="", lecture_category_func=lambda lecture_name: lecture_name):
        # all_embeddings    {embeddings: {"source", "embedding", "sourcelength", "id", "topic"}}
        all_embeddings = []
        embeddings = []
        article={'embeddings': embeddings}
        all_embeddings.append(article)

        category_mapping = {}
        # {"name": str, "slides": {"header": header, "text": text, "page": slide_count}}
        for lecture in lectures:
            lecture_name = lecture["name"]
            lecture_category = lecture_category_func(lecture_name)
            # Match to any of the categories
            matching_category = None
            for cat in categories:
                if lecture_category.startswith(cat):
                    matching_category = cat
                    break
            # If none match, then use the misc category
            if matching_category == None:
                matching_category = misc_category
                
            # If the category is not yet mapped, then add a new empty list
            if not(matching_category in category_mapping):
                category_mapping[matching_category] = []
            content = category_mapping[matching_category]

            slides = lecture["slides"]
            for slide in slides:
                # Add all slides to content
                # Retain the original lecture and all slide infos
                new_slide = slide.copy()
                new_slide["lecture"] = lecture_name
                content.append(new_slide)
            
                header = slide["header"]
                # Build the source from the slides text, tables etc.
                source = header + ":\t" + slide["text"]
                source = source + (("\ttables: "+ str(slide["tables"])) if "tables" in slide and len(slide["tables"]) > 0 else "")
                source = source + (("\timages: "+ str(slide["images"])) if "images" in slide and len(slide["images"]) > 0 else "")
                source = source + (("\tvideos: "+ str(slide["videos"])) if "videos" in slide and len(slide["videos"]) > 0 else "")

                page = slide["page"]
                embedding = self.embedder.embed_chunks([{"content": source}]).tolist()[0]
                # print(f"embedding: {embedding} {len(embedding[0])} {len(embedding.tolist()[0])}")
                emb = {"source": source, "embedding": embedding, "sourcelength": len(source), "id": "-1", "topic": matching_category, "lecture": lecture_name, "page": page, "header": header}
                embeddings.append(emb)

        print("Embedding done")

        return all_embeddings
