
import json

import marko



def lectures_to_html(lectures):
   content = ""

   html_lectures = []

   for lecture in lectures:
      lecture_name = lecture["name"]

      slides = lecture["slides"]
      for slide in slides:

         print(slide["text"])
         print(marko.convert(slide['text']))

         content = content + f"<h1>{slide['header']}</h1>{marko.convert(slide['text'])}"

      html_lecture = {"name": lecture_name, "html": ""}
      html_lecture["html"] = "<!doctype html><html lang=\"de\"><head></head><body>" + content + "</body></html>"
      html_lectures.append(html_lecture)

      content = ""
      # Break after first lecture
      # break
   
   return html_lectures


if __name__ == '__main__':

   with open("lectures.json", "r", encoding="utf-8") as file:
      lectures = json.load(file)
      
      html_lectures = lectures_to_html(lectures)

      for lecture in html_lectures:
         with open(lecture["name"]+".html", "w", encoding="utf-8") as f:
            f.write(lecture["html"])