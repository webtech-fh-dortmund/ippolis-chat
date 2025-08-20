
from pathlib import Path
from datetime import datetime

from ollama_rag import call_ollama
from ollama_images import open_image, send_images_ollama

def create_alternative_image_texts(lectures, app_config):
   skip_until_image = ("", "")

   images_to_skip = ["css-regel-selektor", "css-combinators-children", "css-combinators-descendantcombinator", "css-box-model-props-dim", 
                     "three-tier-architecture-2", "tiered-mvc-3"]

   skipping = False
   
   with open('image_summary_full.txt', 'r', encoding="utf-8") as file:
      content = file.read()
      split = content.split("###")

   with open('image_summary.txt', 'w', encoding="utf-8") as file:
    i = 0
    for lecture in lectures:
        print(lecture["name"])
        for slide in lecture["slides"]:
           for img in slide["images"]:

            # if slide["page"] <= 6:
            #    break

            # Skip all images that have no new alt text
            # By skipping until the next image with alt text is reached
            src = split[i]
            print(f"src: {src} {img['src']} {src == img['src']}")
            if img["src"] != src:
               continue
            i = i+2
            if i > len(split):
               break

            image_name = Path(img["src"]).stem

            if image_name in images_to_skip:
               continue

            # Skip images until the desired start has been reached
            if skip_until_image[1] == "" or (lecture["name"] == skip_until_image[0] and image_name == skip_until_image[1]):
               skipping = False
            if skipping:
               continue
            if img["src"].endswith(".svg"):
               continue

            print(image_name)

            model = "llava:7b"
            model = "llama3.2-vision"

            ollama_ip = "http://192.168.0.253:11434"

            scaled_image = open_image(img["full_path"], 800, 800)

            prompt = f"Beschreibe die Grafik: \"{image_name}\" in einem zusammenhängenden Absatz. Antworte kurz und sachlich. Beschreibe nur die sichtbaren Elemente und Texte der Grafik. Antworte mit maximal 120 Zeichen."
            # prompt = f"Write an alt-text, that describes this image with the title \"{image_name}\"."
            
            starttime = datetime.now()
            print(f"Describe image started: "+starttime.strftime('%Y-%m-%d %H:%M:%S'))
            
            # answer = send_images_ollama([scaled_image], prompt, model, ollama_ip)
            
            description = split[i+1]

            user_query = f"Schreibe einen Alternativtext für ein Bild mit dem Titel {image_name}. Das übergeordnete Thema ist {slide['header']}. Antworte kurz und präzise. Antworte nur mit dem Alternativtext. Benutze diesen Text als Grundlage: {description}"
            answer = call_ollama(user_query, "", app_config)


            endtime = datetime.now()
            print(f"Describe image done: "+endtime.strftime('%Y-%m-%d %H:%M:%S'))

            print(answer)

            slide_title = slide["header"]
            print(slide_title)

            system_prompt = ""#"Befolge genau die Anweisungen."
            # Top für ARPA-Logo
            user_query = f"Schreibe einen alternativ Text für ein Bild mit dem Titel {image_name}. Benutze diesen Text als Grundlage: {answer}"
            # Ok
            user_query = f"Schreibe einen alternativ Text für ein Bild mit dem Titel {image_name}. Das übergeordnete Thema ist {slide_title}. Benutze diesen Text als Grundlage: {answer}"
            # Ok, aber oft einfach nur übersetzt
            user_query = f"Schreibe einen alternativ Text für ein Bild mit dem Titel {image_name}. Das übergeordnete Thema ist {slide_title}. Benutze diesen Text als Grundlage: {answer}. Ändere keine elementaren Aussagen des Textes."
            user_query = f"Schreibe einen alternativ Text für ein Bild mit dem Titel {image_name}. Das übergeordnete Thema ist {slide_title} und dies sind Zusatzinformationen: \"{slide['text']}\". Benutze diesen Text als Grundlage: {answer}. Ändere keine elementaren Aussagen des Textes."
            user_query = f"Schreibe einen alternativ Text für ein Bild mit dem Titel {image_name}. Das übergeordnete Thema ist {slide_title} und dies sind Zusatzinformationen: \"{slide['text']}\". Benutze diesen Text als Grundlage: {answer}."
            user_query = f"Schreibe einen alternativ Text für ein Bild mit dem Titel {image_name}. Das übergeordnete Thema ist {slide_title} und dies sind Zusatzinformationen: \"{slide['text']}\". Benutze diesen Text als Grundlage: {answer}. Behalte die originalen Informationen weitgehend bei."
            # Maybe nice
            system_prompt = "Answer in a matter-of-fact style."
            user_query = f"Schreibe eine Beschreibung für ein Bild mit dem Titel {image_name}. Das übergeordnete Thema ist {slide_title}. Benutze diesen Text als Grundlage: {answer}"
            # user_query = f"Schreibe eine kurze Beschreibung für ein Bild mit dem Titel {image_name}. Das übergeordnete Thema ist {slide_title}. Benutze diesen Text als Grundlage: {answer}"
            user_query = f"Schreibe einen Alternativtext für ein Bild mit dem Titel {image_name}. Das übergeordnete Thema ist {slide_title}. Antworte kurz und präzise. Benutze diesen Text als Grundlage: {answer}"
            # Top
            user_query = f"Schreibe einen Alternativtext für ein Bild mit dem Titel {image_name}. Das übergeordnete Thema ist {slide_title}. Antworte kurz und präzise. Antworte nur mit dem Alternativtext. Benutze diesen Text als Grundlage: {answer}"
            # description = call_ollama(user_query, system_prompt, app_config)

            file.write(f"{img['src']}###{answer}###")

            # break
         #   if slide["page"] == 6:
         #      break
      #   break
