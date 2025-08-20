
import json
import requests
import pprint
from sentence_transformers import SentenceTransformer
import copy
import sys
import pprint
from math import ceil

base_path = ""

def read_json_file(filepath):
   with open(filepath, "r", encoding="utf-8") as file:
      return json.load(file)

def write_json_file(obj, filepath):
   with open(filepath, "w", encoding="utf-8") as file:
      json.dump(obj, file, ensure_ascii=False)

def get_studiengaenge_ids(stundenplan_ids):
    studiengaenge_ids = []
   # Filter out all stundenplaene, that are no studiengang ids
    studiengaenge_exclusions = ["blockwoche", "feminf", "wfpb", "tupb", "qdl", "smpb"]
    for sp_id in stundenplan_ids:
      # A studiengang id is to be included if it matches to none of the excluded ones
       if len([sp_id for sp_e in studiengaenge_exclusions if sp_id.lower().startswith(sp_e)]) == 0:
          studiengaenge_ids.append(sp_id)
    return studiengaenge_ids

def get_stundenplaene(stundenplaene: json, filepath=None):
    result = []
    for stundenplan_id in stundenplaene:
      # print(stundenplan_id)
       sp = stundenplaene[stundenplan_id]
      # "Bachelor Informatik (StgPO 2019), VR Praktische Inf.", "Blockwoche 3 (20.01. - 24.01.2025)", "FemINF (Tutorium für Studentinnen)" etc.
       name = sp["name"] if "name" in sp else "Unnamed"
      # "2018" etc.
       po = sp["po"] if "po" in sp else "No PO"
      # ["1-7"|"*"]
       grades = [grade["grade"] for grade in sp["grades"]] if "grades" in sp else []

       for grade in grades:
          result.append({"name": name, "po": po, "grade": grade, "studiengang_id": stundenplan_id})

    if filepath != None:
         write_json_file(result, filepath)

    return result

def get_studiengaenge(stundenplaene, studiengaenge_ids, filepath=None):
   result = []

   for sp in stundenplaene:
      if sp["studiengang_id"] in studiengaenge_ids:
         # If the same name is not yet contained in result
         if len([r for r in result if r["name"] == sp["name"]]) == 0:
            result.append({"name": sp["name"], "studiengang_id": sp["studiengang_id"], "po": sp["po"]})

   if filepath != None:
         write_json_file(result, filepath)

   return result

def get_veranstaltungen(studiengang_id, semester, filepath=None):
   stundenplan_url = f"enter_url_here/{studiengang_id}/{semester}/Events?Accept=application/json"

   response = requests.get(stundenplan_url)
   veranstaltungen = json.loads(response.text)

   veranstaltungen_neu = []
   # If data is returned, e.g. a stundenplan has been found for the given id and semester
   if len(veranstaltungen) >= 0:
      # "courseOfStudy" can also be e.g. "Blockwoche1-3", "WFPB", "FemINF", "TUPB", "SMPB", "QDL"
      attributes_to_keep = ['courseId', 'courseOfStudy', 'courseType', 'grade', 'interval', 'lecturerName', 'lecturerSurname'
                           'name', 'roomId', 'studentSet', 'termId', 'timeBegin', 'timeEnd', 'weekday']
      # Ignored attributes: 'lecturerSurname', 'lecturerId', ...
      
      i = 0
      for entry in veranstaltungen:
         neue_veranstaltung = {"id": i}
         for attr in attributes_to_keep:
            neue_veranstaltung[attr] = entry[attr] if attr in entry else ""
         veranstaltungen_neu.append(neue_veranstaltung)
         i = i + 1

      if filepath != None:
         write_json_file(veranstaltungen_neu, filepath)

   return veranstaltungen_neu

def translate_attributes(veranstaltungen_neu, studiengaenge):
   attribute_mapping = {'courseOfStudy': dict((sg["studiengang_id"], sg["name"]) for sg in studiengaenge),
                        'courseType': {'PR': 'Projekt', 'T': 'Tutorium', 'SV': 'Seminarvorlesung', 
                                       'Ü': 'Übung', 'ÜPP': 'Praktikum-Übung', 'S': 'Seminar', 'P': 'Praktikum', 'V': 'Vorlesung'},
                        'weekday': {'Mon': 'Montag', 'Tue': 'Dienstag', 'Wed': 'Mittwoch', 'Thu': 'Donnerstag', 'Fri': 'Freitag', 'Sa': 'Samstag', 'So': 'Sonntag'}
                        # 'weekday': {'Mon': 'Mo', 'Tue': 'Di', 'Wed': 'Mi', 'Thu': 'Do', 'Fri': 'Fr', 'Sa': 'Sa', 'So': 'So'}
                        }
   attribute_name_mapping = {'grade': 'Semester', 'roomId': 'Raum', 'timeBegin': 'Startzeit', 'timeEnd': 'Endzeit', 'studentSet': 'Gruppenbuchstabe', 
                              'weekday': 'Wochentag', 'courseOfStudy': 'Studiengänge', 'termId': 'Winter/Sommer', 'lecturerName': 'Dozent*in', 'lecturerSurname': 'Dozent*in Nachname'}
   # Für Einträge mit 'WFPB' für 'courseOfStudy' stehen die Studiengänge i.d.R. im Namen der Veranstaltung
   attribute_mapping['courseOfStudy']['WFPB'] = 'Wahlpflichtfach'

   for veranstaltung in veranstaltungen_neu:
      # Mapp all values of the chosen attributes to the new values
      for am in attribute_mapping:
         # If the attribute is a list, e.g. multiple courseOfStudy, then translate each of them
         if isinstance(veranstaltung[am], list):
            i = 0
            for attr in veranstaltung[am]:
               # if it has a mapping
               if attr in attribute_mapping[am]:
                  veranstaltung[am][i] = attribute_mapping[am][attr]
               i = i + 1
         else:
            # Otherwise just translate the attribute if it has a mapping
            if veranstaltung[am] in attribute_mapping[am]:
               veranstaltung[am] = attribute_mapping[am][veranstaltung[am]]
      # Rename the chosen attributes and delete the old names
      for anm in attribute_name_mapping:
         veranstaltung[attribute_name_mapping[anm]] = veranstaltung[anm]
         del veranstaltung[anm]

def print_interesting_attributes(veranstaltungen_neu):
   # Print each possible appearing value of the most interesting attributes
   interesting_attributes = {}
   interesting_attributes["courseType"] = set([v['courseType'] for v in veranstaltungen_neu])
   interesting_attributes["courseOfStudy"] = set([v['courseOfStudy'] for v in veranstaltungen_neu])
   interesting_attributes["grade"] = set([v['grade'] for v in veranstaltungen_neu])
   interesting_attributes["interval"] = set([v['interval'] for v in veranstaltungen_neu])
   # "Online", "*" (in this case the rooms are defined in "name")
   interesting_attributes["roomId"] = set([v['roomId'] for v in veranstaltungen_neu])
   interesting_attributes["termId"] = set([v['termId'] for v in veranstaltungen_neu])
   interesting_attributes["studentSet"] = set([v['studentSet'] for v in veranstaltungen_neu])
   interesting_attributes["weekday"] = set([v['weekday'] for v in veranstaltungen_neu])
   # These may be excluded, since printing these takes up a lot of space
   # interesting_attributes["name"] = set([v['name'] for v in veranstaltungen_neu])
   # interesting_attributes["lecturerName"] = set([v['lecturerName'] for v in veranstaltungen_neu])

   pp = pprint.PrettyPrinter(depth=4, width=800)
   pp.pprint(interesting_attributes)

def veranstaltungen_filter(filter_lambda, veranstaltungen_neu):
   """
   To be used like e.g. <br> <code> veranstaltungen_filter(lambda v: v["courseType"] == "PR", veranstaltungen_neu) </code>
   """
   return [v for v in filter(filter_lambda, veranstaltungen_neu)]

def add_aliases(veranstaltungen_neu):
   all_veranstaltung_names = set([v['name'] for v in veranstaltungen_neu])

   json_all_veranstaltung_names = json.dumps([f for f in all_veranstaltung_names], ensure_ascii=False)
   print(json_all_veranstaltung_names)


   # json_all_veranstaltung_names = json.dumps([v['name'] for v in veranstaltungen_neu], ensure_ascii=False)
   # print(json_all_veranstaltung_names)
   # pp = pprint.PrettyPrinter(depth=4, width=800)
   # pp.pprint(set([v['name'] for v in veranstaltungen_neu]))

   # system_prompt = "Die folgende Liste enthält Namen von Veranstaltungen. Gibt zu jedem Veranstaltungsnamen eine Abkürzung aus. Antworte im JSON-Format:"
   # user_query = str(json_all_veranstaltung_names)

   # answer = send_msg_ollama(system_prompt, user_query, [[{}]])

def improve_aliases():
   alias_mapping = read_json_file(base_path+"data/stundenplan/modul_alias_mapping.json")
   
   # Sort them ascending based on name
   sorted_list = sorted(alias_mapping, key=lambda am: am["Name"], reverse=False)

   pp = pprint.PrettyPrinter(depth=4, width=800)
   pp.pprint(sorted_list)

   write_json_file(sorted_list, base_path+"data/stundenplan/modul_alias_mapping_sorted.json")


def prepare_data():
   """
   Reads all remote data and sets up local files
   """

   alle_stundenplaene_url = "enter_url_here"

   response = requests.get(alle_stundenplaene_url)

   js = json.loads(response.text)

   stundenplan_ids = [stundenplan for stundenplan in js]

   # [INPBPI, INPBTI, INPM etc.]
   studiengaenge_ids = get_studiengaenge_ids(stundenplan_ids)

   # [{"name", "po", "grade", "studiengang_id"}]
   stundenplaene = get_stundenplaene(js, base_path+"data/stundenplan/alle_stundenplaene_raw.json")

   studiengaenge = get_studiengaenge(stundenplaene, studiengaenge_ids, base_path+"data/stundenplan/alle_studiengaenge.json")
   
   veranstaltungen_neu = get_veranstaltungen("*", "*", "data/stundenplan/alle_stundenplaene.json")
   
   translate_attributes(veranstaltungen_neu, studiengaenge)

   write_json_file(veranstaltungen_neu, base_path+"data/stundenplan/alle_stundenplaene_mapped.json")

   pp = pprint.PrettyPrinter(depth=4)
   pp.pprint(veranstaltungen_neu)
   print(f"Veranstaltungen count: {len(veranstaltungen_neu)}")

   return veranstaltungen_neu

def combine_entries(veranstaltungen_mapped):
   result = []
   doublettes = {}
   # combine lv if weekday, roomId, timeBegin and timeEnd are equal => combine courseOfStudy
   for lv in veranstaltungen_mapped:
      key = lv["weekday"]+lv["roomId"]+lv["timeBegin"]+lv["timeEnd"]
      # If a matching lv already exists, then add the course of study of this lv to the other one
      if key in doublettes:
         # Only add it, if it's not added already
         if not(lv["courseOfStudy"] in doublettes[key]["courseOfStudy"]):
            doublettes[key]["courseOfStudy"].append(lv["courseOfStudy"])
      else:
         # If no matching lv was processed yet, then add it
         # also change course of study to array - TODO do way earlier in the crawling / preprocessing
         lv["courseOfStudy"] = [lv["courseOfStudy"]]
         doublettes[key] = lv
         result.append(lv)
   return result

def transform_data():
   # veranstaltungen_neu = prepare_data()

   # "*" for all
   # studiengang_id = "INDBNS"#stundenplan_ids[5]
   # studiengang_id = "*"
   # semester = "*"

   studiengaenge = read_json_file(base_path+"data/stundenplan/alle_studiengaenge.json")

   # veranstaltungen_neu = read_json_file(base_path+"data/stundenplan/alle_stundenplaene.json")


   # TODO for testing only - only use a tiny subset
   # veranstaltungen_neu = veranstaltungen_neu[0:10]

   
   # translate_attributes(veranstaltungen_neu, studiengaenge)


   # veranstaltungen_mapped = read_json_file(base_path+"data/stundenplan/alle_stundenplaene_mapped.json")
   veranstaltungen_mapped = read_json_file(base_path+"data/stundenplan/alle_stundenplaene.json")


   # TODO tmp only: add lecturerSurname since it is not in the current persisted json files
   for lv in veranstaltungen_mapped:
      lv['lecturerSurname'] = lv['lecturerName']

   # Add ":" to start and end time
   for lv in veranstaltungen_mapped:
      lv['timeBegin'] = lv['timeBegin'][:2] + ':' + lv['timeBegin'][2:]
      lv['timeEnd'] = lv['timeEnd'][:2] + ':' + lv['timeEnd'][2:]

   # TODO for testing only - only use a tiny subset
   # veranstaltungen_mapped = veranstaltungen_mapped[0:10]

   # pp = pprint.PrettyPrinter(depth=4)
   # pp.pprint(veranstaltungen_mapped)

   # user_query = "Wann findet Datenbanken statt?"
   # user_query = "Wann ist die DB 1 Übung?"
   # embedding_search(veranstaltungen_mapped, user_query)

   veranstaltungen_mapped = combine_entries(veranstaltungen_mapped)

   veranstaltungen_translated = copy.deepcopy(veranstaltungen_mapped)
   translate_attributes(veranstaltungen_translated, studiengaenge)

   return veranstaltungen_translated

def embedding_search(raw_data, user_query, rag, file=None, attribute_search=[]):
    
    print("Question: "+user_query)

    encoder_model = get_encoder_model()

    question_embedding = encoder_model.encode([user_query])

    print(f"Embedding search via {attribute_search}")

    if len(attribute_search) != 0:
        # Embed all attributes
        # Differ if only 1 attribute should be used
        if len(attribute_search) == 1:
            embeddings = encoder_model.encode([["", v[attribute_search[0]]] for v in raw_data]) # Returns a NumPy array
        else:
            embeddings = encoder_model.encode([[v[attr] for attr in attribute_search] for v in raw_data]) # Returns a NumPy array
        
        # Embed and search with each individual attribute
        # for a in attribute_search:
        #     # Encode lists as strings, since they can not directly encoded
        #     embeddings = encoder_model.encode([("", a) if isinstance(a, list) else (a) for v in raw_data]) # Returns a NumPy array
        # Hybrid: maybe embed all attributes and then search with individual ones and add the best matches
    else:
        # Embed the whole lv
        embeddings = encoder_model.encode([str(v) for v in raw_data]) # Returns a NumPy array

    k = 100
    best_matches = rag.knn_search(question_embedding, embeddings, k)

    # print(best_matches)
    # print(raw_data)

    # [(distance, lv)]
    best_veranstaltungen = [(bm[1], raw_data[bm[0]]) for bm in best_matches]

    # Only keep the ones above a certain threshold (maybe 0.52)
    threshold = 0.55
    best_veranstaltungen = [(bm[1], raw_data[bm[0]]) for bm in best_matches if bm[1] < threshold]

    # If not a specific number of matches has been reached, increase the threshold linearly until a maximum
    target_count = 5
    threshold_step = 0.01
    max_threshold = max(threshold, 0.6)
    while len(best_veranstaltungen) < target_count and threshold < max_threshold:
        threshold = threshold + threshold_step
        best_veranstaltungen = [(bm[1], raw_data[bm[0]]) for bm in best_matches if bm[1] < threshold]

    # Both methods are somewhat exchangeable. But if the maximum threshold still fails, then the best quartil/tertil of all matches still selects some.

    # only use the best upper 25, 33, 50, 66, 75, 100% of matches
    match_count = len(best_matches)
    percent_thresholds = [25, 33, 50, 66, 75, 100]
    while len(best_veranstaltungen) == 0:
        end_index = ceil(match_count*percent_thresholds.pop(0)/100.0)
        best_veranstaltungen = [(bm[1], raw_data[bm[0]]) for bm in best_matches[0:end_index]]



    # print(best_veranstaltungen)
    pp = pprint.PrettyPrinter(depth=4, width=1200)
    # Write to file instead
    if file != None:
        pp = pprint.PrettyPrinter(depth=4, width=1200, stream=file)
    
    #  (0.53201234,
    # {'courseId': '42073',
    # 'courseOfStudy': 'WIPB',
    # 'courseType': 'Ü',
    # 'grade': '3',
    # 'id': 139,
    # 'interval': 'weekly',
    # 'lecturerName': 'Prof. Dr. Kuhnt',
    # 'name': 'Mathematik für Informatik 3 / Statistik (WI)',
    # 'roomId': 'A.2.03',
    # 'studentSet': 'D-F',
    # 'termId': 'WS 2024/25',
    # 'timeBegin': '830',
    # 'timeEnd': '1005',
    # 'weekday': 'Tue'})]
    # attribute_name_mapping: {'grade': 'Semester', 'roomId': 'Raum', 'timeBegin': 'Startzeit', 'timeEnd': 'Endzeit', 'studentSet': 'Gruppenbuchstabe', 
    #                         'weekday': 'Wochentag', 'courseOfStudy': 'Studiengänge', 'termId': 'Winter/Sommer', 'lecturerName': 'Dozent*in', 'lecturerSurname': 'Dozent*in Nachname'}
    def lv_attributes_string_short(lv):
        # return f"{lv['name']} {lv['courseType']} {lv['lecturerName']} {lv['weekday']} {lv['timeBegin']}-{lv['timeEnd']}"# {lv['courseOfStudy']}
        # for testing
        # return f"{lv['name']} {lv['courseType']} {lv['weekday']} {lv['roomId']} {lv['timeBegin']}-{lv['timeEnd']} {lv['courseOfStudy']} {lv['lecturerName']}"
        # top
        # return f"{lv['name']} {lv['courseType']} {lv['Wochentag']} {lv['Raum']} {lv['Startzeit']}-{lv['Endzeit']} {lv['Studiengänge']} {lv['Dozent*in']}"
        # short
        return f"{lv['name']} {lv['courseType']} {lv['Wochentag']} {lv['Raum']} {lv['Startzeit']}-{lv['Endzeit']} {lv['Dozent*in']}"
        # return f"{lv['name']} Typ: {lv['courseType']} {lv['Wochentag']} Raum: {lv['Raum']} {lv['Startzeit']}-{lv['Endzeit']} {lv['Dozent*in']}"
        # return f"{'{'}Name: {lv['name']}, Typ: {lv['courseType']}, Wochentag: {lv['Wochentag']}, Raum: {lv['Raum']}, Start: {lv['Startzeit']}, Ende: {lv['Endzeit']}, Dozent*in: {lv['Dozent*in']}{'}'}"
        # return f"{'{'}'Name': {lv['name']}, 'Typ': {lv['courseType']}, 'Wochentag': {lv['Wochentag']}, 'Raum': {lv['Raum']}, 'Start': {lv['Startzeit']}, 'Ende': {lv['Endzeit']}, 'Dozent*in': {lv['Dozent*in']}{'}'}"
        # return f"{'{'}\"Name\": {lv['name']}, \"Typ\": {lv['courseType']}, \"Wochentag\": {lv['Wochentag']}, \"Raum\": {lv['Raum']}, \"Start\": {lv['Startzeit']}, \"Ende\": {lv['Endzeit']}, \"Dozent*in\": {lv['Dozent*in']}{'}'}"
        # combine start and end
        return f"{'{'}\"Name\": {lv['name']}, \"Typ\": {lv['courseType']}, \"Wochentag\": {lv['Wochentag']}, \"Raum\": {lv['Raum']}, \"Uhrzeit\": {lv['Startzeit']}-{lv['Endzeit']}, \"Dozent*in\": {lv['Dozent*in']}{'}'}"
        # Switch typ to front
        # return f"{lv['courseType']} {lv['name']} {lv['Wochentag']} {lv['Raum']} {lv['Startzeit']}-{lv['Endzeit']} {lv['Dozent*in']}"
        # return f"{'{'}\"Typ\": {lv['courseType']}, \"Name\": {lv['name']}, \"Wochentag\": {lv['Wochentag']}, \"Raum\": {lv['Raum']}, \"Uhrzeit\": {lv['Startzeit']}-{lv['Endzeit']}, \"Dozent*in\": {lv['Dozent*in']}{'}'}"
        # as CSV
        # return f"{lv['name']}, {lv['courseType']}, {lv['Wochentag']}, {lv['Raum']}, {lv['Startzeit']}, {lv['Endzeit']}, {lv['Dozent*in']}"
    # best_veranstaltungen_short = [f"{bv[0]}, {lv_attributes_string_short(bv[1])}" for bv in best_veranstaltungen]
    # without distance
    best_veranstaltungen_short = [f"{lv_attributes_string_short(bv[1])}" for bv in best_veranstaltungen]
    # Add CSV header
    # best_veranstaltungen_short.insert(0, "Name, Typ, Wochentag, Raum, Start, Ende, Dozent*in")
    # pp.pprint(best_veranstaltungen)

    # TODO for testing only - only use a tiny subset
    # best_veranstaltungen_short = best_veranstaltungen_short[0:10]

    # pp.pprint(best_veranstaltungen_short)


    print(f"Count: {len(best_veranstaltungen)}")
    print(f"Avrg: {sum([bv[0] for bv in best_veranstaltungen]) / len(best_veranstaltungen) if len(best_veranstaltungen) > 0 else ''}")
    print(f"Min: {best_veranstaltungen[0][0] if len(best_veranstaltungen) > 0 else ''}")
    print(f"Min: {best_veranstaltungen[-1][0] if len(best_veranstaltungen) > 0 else ''}")



    # TODO continue
    # best_veranstaltungen = best_veranstaltungen[0:10]

    # best_veranstaltungen_short = best_veranstaltungen_short[0:20]
    best_veranstaltungen_short = best_veranstaltungen_short[0:15]
    best_veranstaltungen = best_veranstaltungen_short
    pp.pprint(best_veranstaltungen_short)
    # Convert to json and back
    # best_veranstaltungen_short = json.loads(json.dumps(best_veranstaltungen_short))

    # print(str(best_veranstaltungen))
    # system_prompt = f"Benutze ausschließlich den folgenden Stundenplan im JSON Format, um Fragen zu beantworten: {best_veranstaltungen}"
    # system_prompt = f"Du kannst Fragen zu diesem Stundenplan im JSON Format beantworten: {best_veranstaltungen}"
    # system_prompt = f"Du kannst Fragen zu diesem Stundenplan im CSV Format beantworten: {best_veranstaltungen}"
    system_prompt = f"Du kannst Fragen zu diesem Stundenplan beantworten: {best_veranstaltungen}"
    # system_prompt = f"Du beantwortest Fragen zum Stundenplan im JSON Format: {best_veranstaltungen}"
    # system_prompt = f"Benutze ausschließlich den folgenden Stundenplan, um Fragen zu beantworten: {best_veranstaltungen}"

    return system_prompt

    # Write all veranstaltungen to file
    
    # raw_data = sorted(raw_data, key=lambda am: am["name"], reverse=False)
    # with open('out.txt', 'w', encoding="utf-8") as f:
    #     pp = pprint.PrettyPrinter(depth=4, width=1200, stream=f)
    #     pp.pprint([lv_attributes_string_short(lv) for lv in raw_data])

def get_encoder_model():
    return SentenceTransformer('all-MiniLM-L6-v2')


if __name__ == '__main__':
   from ollama_rag import send_msg_ollama, send_to_ollama, RAG

   veranstaltungen_translated = transform_data()

   write_to_file = False

   f = None
   if write_to_file:
      orig_stdout = sys.stdout
      f = open('out.txt', 'a', encoding="utf-8")
      sys.stdout = f

   encoder_model = get_encoder_model()
   rag = RAG()
   with open("Stundenplan_Fragen.txt", "r") as file:
   # with open("Stundenplan_Fragen_wrong_context.txt", "r") as file:
      for line in file.readlines():
         # embedding_search(veranstaltungen_mapped, line)
         
         line = "Woher weiß ich, was in der Blockwoche ansteht?"
         line = "Wann ist die Web-Tech Vorlesung?"
         line = "Wann sind donnerstags und freitags die Übungen von Web-Tech?"
         line = "Wann sind mittwochs und freitags die Übungen von Web-Tech?"
         # line = "Wann sind die Praktika von Programmierkurs 1?"
         # line = "Wann sind die Praktika von Datenbanken 1?"
         # line = "Wann sind die Praktika von Softwaretechnik 1?"
         # line = "Wann sind die Praktika von Rechnerstrukturen und Betriebssysteme 1?"

         # # Use attributes in this order for the additional embed searches
         # #  name, courseType, lecturerName, weekday, courseOfStudy
         # # attribute_name_mapping:
         # # {'grade': 'Semester', 'roomId': 'Raum', 'timeBegin': 'Startzeit', 'timeEnd': 'Endzeit', 'studentSet': 'Gruppenbuchstabe', 
         # #  'weekday': 'Wochentag', 'courseOfStudy': 'Studiengänge', 'termId': 'Winter/Sommer', 'lecturerName': 'Dozent*in', 'lecturerSurname': 'Dozent*in Nachname'}

         # embedding_search(veranstaltungen_translated, line, rag, f)

         # embedding_search(veranstaltungen_translated, line, rag, f, attribute_search=["name"])
         # embedding_search(veranstaltungen_translated, line, rag, f, attribute_search=["name", "courseType"])
         # embedding_search(veranstaltungen_translated, line, rag, f, attribute_search=["name", "courseType", "Dozent*in Nachname"])
         # embedding_search(veranstaltungen_translated, line, rag, f, attribute_search=["name", "courseType", "Dozent*in Nachname", "Wochentag"])
         # embedding_search(veranstaltungen_translated, line, rag, f, attribute_search=["name", "courseType", "Dozent*in Nachname", "Wochentag", "Studiengänge"])

         # embedding_search(veranstaltungen_translated, line, rag, f, attribute_search=["name"])
         # embedding_search(veranstaltungen_translated, line, rag, f, attribute_search=["courseType"])
         # embedding_search(veranstaltungen_translated, line, rag, f, attribute_search=["Dozent*in Nachname"])
         # embedding_search(veranstaltungen_translated, line, rag, f, attribute_search=["Wochentag"])
         # embedding_search(veranstaltungen_translated, line, rag, f, attribute_search=["Studiengänge"])
         
         send_to_ollama(embedding_search(veranstaltungen_translated, line, rag, f, attribute_search=["name", "courseType", "Dozent*in Nachname", "Wochentag", "Studiengänge"]), line)

         # Break after just 1 question
         break

   if write_to_file:
      sys.stdout = orig_stdout
      f.close()



   # add_aliases(veranstaltungen_neu)



   # for v in veranstaltungen_neu:
   #    print(v["name"])

   # veranstaltungen_neu = veranstaltungen_filter(lambda v: v["courseType"] == "ÜPP", veranstaltungen_neu)
   # veranstaltungen_neu = veranstaltungen_filter(lambda v: v["courseOfStudy"] == "WFPB", veranstaltungen_neu)

   # pp = pprint.PrettyPrinter(depth=4)
   # pp.pprint(veranstaltungen_neu)
   # print(f"Veranstaltungen count: {len(veranstaltungen_neu)}")

   # print_interesting_attributes(veranstaltungen_neu)

