
import re
import json
from web_tech_crawler import crawl_lectures, crawl_pdf, Web_Crawler_Config, TagEncoder
from web_tech_image_alt_texts import create_alternative_image_texts
from lecture_knowledge_base import Lecture_Knowledge_Base
from ollama_rag import RAG
import os


enable_search_operators = False

# Convert the alt image file to proper json
# with open("data/image_summary_done.txt", "r", encoding="utf-8") as file:
#     content = file.read()
#     split = content.split("###")
#     pairs = {}
#     i = 0
#     while i < len(split)-1:
#         text = split[i]
#         src = split[i+1]
#         # If an alt text already is assigned
#         # if src in pairs and pairs[src] != text:
#         #     raise Exception(f"Already contained: {src}")
#         pairs[src] = text
#         i = i+2
#     with open("data/web_bot_image_alt_texts.json", "w", encoding="utf-8") as file:
#         json.dump(pairs, file)

# Either craw the lectures locally
# lectures = crawl_lectures("/web-tech-bot/data/web-tech-slides-wise2425")
# lectures = crawl_pdf("/web-tech-bot/pdfs")
# with open("data/web_bot_lectures.json", "w", encoding="utf-8") as file:
#     json.dump(lectures, file, cls=TagEncoder)
# or use the persisted data
lectures = []
if os.path.isfile("data/web_bot_lectures.json"):
    with open("data/web_bot_lectures.json", "r") as file:
        js = json.load(file)
        for lecture in js:
            lectures.append(lecture)

# create_alternative_image_texts(lectures, app_config)

# Add the new alt text to each image and remove all other image infos
if os.path.isfile("data/web_bot_image_alt_texts.json"):
    with open("data/web_bot_image_alt_texts.json", "r", encoding="utf-8") as file:
        js = json.load(file)
        for lecture in lectures:
            for slide in lecture["slides"]:
                for img in slide["images"]:
                    # Only change images that have an alt text
                    if img["src"] in js:
                        img["alt"] = js[img["src"]]
                        del img["full_path"]

# Map the ilias id of each lectures to their corresponding lecture
lecture_id_mapping = {}
if os.path.isfile("data/web_bot_lectures_id_mapping.json"):
    with open("data/web_bot_lectures_id_mapping.json", "r", encoding="utf-8") as file:
        js = json.load(file)
        for mapping in js:
            key = next(iter(mapping))
            if key in mapping:
                lecture_id_mapping[key] = mapping[key]

def create_knowledge_base(app_config, new_lectures=None, crawler_config=Web_Crawler_Config()):
    return Lecture_Knowledge_Base(app_config, "Web-Bot", lectures if new_lectures == None else new_lectures, crawler_config.categories, crawler_config.misc_category, lecture_category=crawler_config.lecture_category)

def custom_metadata(user_query, app_config, knowledge_base, metadata):

    # Embed the user's question
    question_embedding = knowledge_base.embedder.embed_user_query(user_query)

    # Always find a fixed number of matches via KNN and reduce the number later via a Reranker
    matches_to_find = 10

    # Perform KNN search to find the best matches
    # Index, source_text, topic, distance
    best_matches = RAG().knn_search(question_embedding, knowledge_base.all_embeddings, min(matches_to_find, len(knowledge_base.all_embeddings[0]["embeddings"])))
    

    sources = [item['source'] for article in knowledge_base.all_embeddings for item in article['embeddings']]
    lectures = [item['lecture'] for article in knowledge_base.all_embeddings for item in article['embeddings']]
    pages = [item['page'] for article in knowledge_base.all_embeddings for item in article['embeddings']]
    headers = [item['header'] for article in knowledge_base.all_embeddings for item in article['embeddings']]

    # {lecture, page, source, topic, distance}
    best_matches = [{"lecture": lectures[best_matches[i][0]], "page": pages[best_matches[i][0]], "header": headers[best_matches[i][0]], "src": sources[best_matches[i][0]], 
                     "topic": best_matches[i][2], "distance": best_matches[i][3]} for i in range(len(best_matches))]

    # Now sort based on lecture and page. This will be the secondary sort, e.g. first on KNN distance, then on lecture and page
    best_matches.sort(key=lambda match: match["page"], reverse=False)
    best_matches.sort(key=lambda match: match["lecture"], reverse=False)
    # Sort the best matches based on distance (ascending). This will be the secondary sort.
    best_matches.sort(key=lambda match: match["distance"], reverse=False)

    # Reduce best matches down to 3
    best_matches = best_matches[0:3]

    metadata = []

    for bm in best_matches:
        entry = {}
        metadata.append(entry)
        # Link to the proper ilias page
        if bm["lecture"] in lecture_id_mapping and lecture_id_mapping[bm["lecture"]] != "":
            # The /99/99/99 at the end loads the slide with all animations done (if possible)
            href = f"https://www.ilias.fh-dortmund.de/ilias/data/ilias-fhdo/lm_data/{lecture_id_mapping[bm['lecture']]}/{bm['lecture']}.html#/{bm['page']}" #/99/99/99
            # entry["url"] = f"<a target=\"_blank\" href=\"{href}\">{href}</a>"
            entry["url"] = href
        else:
            entry["url"] = f"No ilias ID found for lecture: {bm['lecture']}"

        entry["Vorlesung"] = bm["lecture"]
        entry["Seite"] = bm["page"]
        entry["KNN-Distanz"] = bm["distance"]
        entry["Inhalt"] = bm["src"]
        entry["Titel"] = bm["header"]

    return metadata

def log_metadata(metadata):
    metadata = json.loads(metadata)
    return [f"[{entry['Vorlesung']}, S. {entry['Seite']}, {entry['Titel']}]" for entry in metadata]

def param_search(string)->tuple[list[str], list[str], list[str]]:
   """
   Searches if the given string includes search parameters like +, - or "" and handles them approriately.
   Returns 3 lists: included, excluded and strict_contained strings.
   """
   debug = False

   if debug:
      print(f"param_search(): {string}")

   includes = []
   # Check for +""
   pattern = re.compile('[^\\\]\+\"(.*?)\"')
   matches = pattern.findall(string)
   string = pattern.sub("", string)
   includes += matches
   if debug:
      print(f"+\"\": {matches}")
   # Check for +
   pattern = re.compile('[^\\\]\+(\S+)')
   matches = pattern.findall(string)
   string = pattern.sub("", string)
   includes += matches
   if debug:
      print(f"+: {matches}")

   excludes = []
   # Check for -""
   pattern = re.compile("[^\\\]-\"(.*?)\"")
   matches = pattern.findall(string)
   string = pattern.sub("", string)
   excludes += matches
   if debug:
      print(f"-\"\": {matches}")
   # Check for -
   pattern = re.compile('[^\\\]\-(\S+)')
   matches = pattern.findall(string)
   string = pattern.sub("", string)
   excludes += matches
   if debug:
      print(f"-: {matches}")

   strict_contains = []
   # Check for ""
   pattern = re.compile("[^\\\]\"(.*?)\"")
   matches = pattern.findall(string)
   string = pattern.sub("", string)
   if debug:
      print(f"\"\": {matches}")
   strict_contains += matches

   if debug:
      print(f"includes: {includes}")
      print(f"excludes: {excludes}")
      print(f"strict_contains: {strict_contains}")

   return includes, excludes, strict_contains

def custom_pre_RAG(user_query, app_config, knowledge_base):
    if not(enable_search_operators):
        return user_query
    # Temporary replace the embeddings via the parametrized search from the user query
    # e.g. if +, - and "" are used in the user query to include or exclude certain patterns

    app_config.tmp_storage["knowledge_base.all_embeddings"] = knowledge_base.all_embeddings
    # [{'embeddings': [{"source", "embedding", "sourcelength", "id", "topic"}]}]
    # additional attributes: "lecture", "page", "header"
    filtered_embeddings = []

    includes, excludes, strict_contains = param_search(user_query)
    # return
    # e.g.:
    # includes: ['test']
    # excludes: ['express']
    # strict_contains: ['no', 'html', 'mvc']

    # Returns true if any of the given strings is in text
    def any_contained(strings: list[str], text: str)->bool:
        for s in strings:
            if s in text:
                return True
        return False
    # Returns true if all of the given strings are in text or the strings list is empty
    def all_contained(strings: list[str], text: str)->bool:
        if len(strings) == 0:
            return True
        for s in strings:
            if not(s in text):
                return False
        return True


    # Iterate over all knowledge_base.all_embeddings and only include those, that match (or not) any of includes, excludes, strict_contains
    # First check for excludes, then strict_contains and includes
    for emb in knowledge_base.all_embeddings:
        eb2 = []
        emb2 = {"embeddings": eb2}
        for eb in emb["embeddings"]:
            source = eb["header"] + " " + eb["source"]
            # print(f"Source:\n\n\n{source}")
            # print(f"{any_contained(excludes, source)} {all_contained(includes, source)} {all_contained(strict_contains, source)}")

            # Continue if any excluded is contained
            if any_contained(excludes, source):
                continue
            # Continue if not all includes and strict matches are contained
            if not(all_contained(includes, source) and all_contained(strict_contains, source)):
                continue
            eb2.append(eb)
            # print(f"\tAdded")
            # print(f"Source:\n\n\n{source}")
        # Only add it if at least one match was added
        if len(eb2) > 0:
            filtered_embeddings.append(emb2)

    knowledge_base.all_embeddings = filtered_embeddings

    return user_query

def custom_post_RAG(user_query, app_config, knowledge_base):
    if not(enable_search_operators):
        return user_query
    # Restore the old embeddings
    knowledge_base.all_embeddings = app_config.tmp_storage["knowledge_base.all_embeddings"]

    return user_query

def on_stop(app_config, knowledge_base):
    if not(enable_search_operators):
        return
    # Restore the old embeddings
    if app_config.tmp_storage["knowledge_base.all_embeddings"] != None and app_config.tmp_storage["knowledge_base.all_embeddings"] != "":
        knowledge_base.all_embeddings = app_config.tmp_storage["knowledge_base.all_embeddings"]
