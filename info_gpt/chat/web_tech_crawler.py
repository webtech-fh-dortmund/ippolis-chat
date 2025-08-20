
import os
from bs4 import BeautifulSoup, Tag
from pathlib import Path
import re
import json

import lecture_crawler
import pdf_crawler
import pymupdf

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
        lines = f.read()
    return lines

class Web_Crawler_Config():
   def __init__(self) -> None:
      self.base_dir = "web-tech-slides-wise2425"
      # Only crawl directories which start with a capital letter followed by a "-"
      self.directory_filter_regexp = "^[A-Z]-"
      self.directories_to_skip = ["A-01-organisatorisches", "A-02-einleitung", "I-abschluss"]
      self.header_to_skip = ["Nächste Lerneinheit", "Web-Technologien", "Themen der Veranstaltung", "Lernziel", "Lernziele"]
      # Zur Kategorisierung der Wissensbasis nach Schlagwörtern
      # Kategorien sollten mit den Anfängen der Dateinamen der Vorlesungen übereinstimmen, z.B. "html" für "C-01-html-einfuehrung-geschichte.html"
      # Mit Außnahme der letzten Kategorie "verschiedenes" für Inhalte ohne eindeutiger Zuordnung
      self.categories = ["html", "css", "javascript", "nodejs", "express", "verschiedenes"]
      self.misc_category = self.categories[len(self.categories)-1]

      def lecture_category(lecture_name):
         # Gets the lecture name without the e.g. "C-06-" for "C-06-html-hyperlinks"
         match = re.search("\w-\d+-(.*)", lecture_name)
         return match.group(1).lower() if match != None else ""
      self.lecture_category = lecture_category
    
      self.tags_to_replace_with_their_text = ["strong", "small", "code"]
      
      self.knowledge_base_dir = "data/knowledge_base"

class TagEncoder(json.JSONEncoder):
    def default(self, obj):
        result = ""
        if isinstance(obj, Tag):
            # {obj.name} 
            if obj.name == "img":
               # result = f"src={obj['src']} alt={obj['alt'] if 'alt' in obj.attrs else 'Kein Alt-Text'}"
               # result = f"\"src\": {obj['src']}"
               # result = json.dumps({"src":obj['src'], "full_path": obj["full_path"]})
               result = {"src":obj['src'], "full_path": obj["full_path"]}
            else:
               result = f"{obj.get_text()}"
        else:
            result = super().default(obj)
        
        return result

# Util methods
def is_tag(element):
   return type(element) == Tag
def find_next_tag(element, name_filter=[]):
   while True:
      element = element.next_element
      if element == None:
         return None
      if is_tag(element) and (len(name_filter) == 0 or element.name in name_filter):
         return element
def all_text(element, element_filter=[], element_replace_with_text_filter=[]):
   text = ""
   if element != None:
   #   soup = BeautifulSoup(element.prettify(), 'html.parser')
      soup = BeautifulSoup(str(element), 'html.parser')
      
      for name in element_replace_with_text_filter:
         for e in soup.find_all(name):
            # Replace the tags with their text. Special case <a> -> "text (link)"
            e.insert_after(e.get_text(strip=True)+(f" ({e.get('href')})" if name == "a" else "")) # Really "strip=True" here?
            e.extract()
      for name in element_filter:
         for e in soup.find_all(name):
            e.extract()
      # Either return the text plain or without all newlines and multiple whitespaces
      return soup.get_text()
   #   for s in soup.stripped_strings:
   #      text = text + s + " "
   #   return text
   return None
def has_class(element, clazz):
   return 'class' in element.attrs and clazz in element['class']
def has_tag_children(tag, child_tag):
   # If any child is a section, then this slide is comprised of subpages
   for child in tag.children:
      if child.name == child_tag:
         return True
   return False

def table_to_json(html_table):
   # Read each th of the header
   # TODO e.g. colspan="2" of th is not handled
   table_header = [[cell.text for cell in col("th")] for col in html_table("thead")][0] if len(html_table("thead")) > 0 else [] # [0] => Ommit the outer array
   
   # Differ between tables with and without tbody
   # Read each td of each tr
   if len(html_table("tbody")) > 0:
      table_body = [[[cell.text for cell in row("td")] for row in body("tr")] for body in html_table("tbody")][0] # [0] => Ommit the outer array
   else:
      table_body = [[cell.text for cell in row("td")] for row in html_table("tr")]

   # Add the header
   table_body.insert(0, table_header)
   # print(json.dumps(table_body))

   return json.dumps(table_body)

def crawl_lecture(root_dir, lecture_files, crawler_config, lectures):
   header_to_skip = crawler_config.header_to_skip
   tags_to_replace_with_their_text = crawler_config.tags_to_replace_with_their_text

   slides = []
   lecture = {"name": Path(lecture_files[0]).stem, "slides": slides}
   lectures.append(lecture)

   soup = BeautifulSoup(read_file(lecture_files[0]), 'html.parser')

   # Replace certain elements with just their content
   for tag in tags_to_replace_with_their_text:
         for t in soup.find_all(tag):
            t.insert_after(t.get_text()) # strip=True
            t.extract()

   # Erwartung: section gefolgt von h1-h6
   # section section wird ignoriert

   slide_count = 0

   for slide in soup.find_all('section'):
         # Skip any slides that are not contained in the PDF
         if has_class(slide, "online-remove"):
            continue
         if has_class(slide, "pdf-remove"):
            # Increase the slide count to properly link to the Ilias Lernmodul
            slide_count = slide_count + 1
            continue

         has_subpages = has_tag_children(slide, "section")
         
         if not(has_subpages):
            next_tag = find_next_tag(slide)

            if next_tag.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
               if next_tag.get_text() in header_to_skip:
                  # Increase the slide count to account for the skipped page
                  slide_count = slide_count + 1
                  continue
               # Replace any newlines in the header
               header = next_tag.get_text().replace("\n", "")
               print(header)
               # Get the text of the content, but remove the header
               # text = slide.get_text().replace(next_tag.get_text(), "", 1)
               # Get the text of the content
               text = all_text(slide, ["table"], ["a"])
               
               # Remove the header from the content
               text = text.replace(next_tag.get_text(), "", 1)
               # Replace any multiple newlines and multiple whitespaces
               # Newlines have to be replaced iteratively to maintain the structure of the lecture
               text = text.replace("   ", "")
               text = text.replace("\n\n\n\n", "\n\n\n")
               text = text.replace("\n\n\n", "\n\n")
               text = text.replace("\n\n", "\n")
               text = text.strip()
               print("######"+text+"###")

               # Handle non text elements
               all_links = slide.find_all('a')
               all_videos = []
               # Videos are <a><img></a> elements
               for link in all_links:
                  tag = find_next_tag(link)
                  if tag != None and tag.name == "img":
                     all_links.remove(link)
                     all_videos.append({"link": link, "alt": tag["alt"]})

               if len(all_videos) > 0:
                  # all_videos = [f"{video['alt']}: {video['link']}" if video["alt"] != "" else "" for video in all_videos] # ignore videos without alt text
                  # all_videos = json.dumps(all_videos)
                  # all_videos = [json.dumps(v, cls=TagEncoder) for v in all_videos]
                  all_videos = [f"{video['alt']}: {video['link']}" for video in all_videos if video["alt"] != ""]

               # Workaround: if a video exists, all images are ignored for now, since the image displays the video's first frame.
               if len(all_videos) > 0:
                  all_images = []
               else:
                  all_images = slide.find_all('img')
                  for img in all_images:
                     img["full_path"] = str(Path(root_dir))+"/"+img["src"]
                  # Convert to json
                  # if len(all_images) > 0:
                  #    all_images = json.dumps([img["alt"] if "alt" in img.attrs else "" for img in all_images]) # ignore images without alt text
                     # Testing only
                     # print(all_images)
                     # return
                  # Convert to json
                  if len(all_images) > 0:
                     # all_images = [json.dumps(v, cls=TagEncoder) for v in all_images]
                     all_images = [{"src":v['src'], "full_path": v["full_path"], "alt": v["alt"]} for v in all_images if "alt" in v.attrs]

               all_tables = slide.find_all('table')
               all_tables = [table_to_json(table) for table in all_tables]
               print(f"all_links {len(all_links)}")
               print(f"all_videos {len(all_videos)}")
               print(f"all_images {len(all_images)}")
               print(f"all_tables {len(all_tables)}")

               #   slides.append({"header": header, "text": text, "page": slide_count})
               slides.append({"header": header, "text": text, "links": all_links, "videos": all_videos, "images": all_images, "tables": all_tables, "page": slide_count})

               # If the slide is just a subpage, then use the parent page number as a workaround
               # TODO should be deleted/changed later
               if slide.parent.name == "section" and has_tag_children(slide.parent, "section"):
                  # Also increase the counter if it is the last child or edge-case: a "\n" might be before it
                  if (slide.parent.contents[len(slide.parent.contents)-1] == slide) or (slide.parent.contents[len(slide.parent.contents)-1] == "\n" and slide.parent.contents[len(slide.parent.contents)-2] == slide):
                     slide_count = slide_count + 1
               else:
                  slide_count = slide_count + 1

def crawl_lectures(directory):
   web_crawler_config = Web_Crawler_Config()

   # Only crawl directories that match the regexp and should not be skipped
   def directory_filter(dir):
      print(f"directory_filter(): {dir}")
      a = re.search(web_crawler_config.directory_filter_regexp, Path(dir).stem)
      b = not(Path(dir).stem in web_crawler_config.directories_to_skip)
      return a and b

   def crawl_directory(dir):
      print(f"dir: {dir}")

      if not(directory_filter(dir)):
         return False

      lecture_files = files_in_dir(dir, ["html"])
      if len(lecture_files) != 1:
         # raise Exception(f"Not exactly 1 html file in directory {dir}")
         print(f"Not exactly 1 html file in directory {dir}")
         for f in lecture_files:
            crawl_lecture(dir, [f], web_crawler_config, crawler.lectures)
      else:
         crawl_lecture(dir, lecture_files, web_crawler_config, crawler.lectures)

      return True

   def crawl_file(f):
      print(f"file: {f}")
      return False

   crawler = lecture_crawler.Crawler(crawl_directory, crawl_file)
   crawler.lectures = []

   crawler_config = lecture_crawler.Crawler_Config(crawler)

   lecture_crawler.crawl_directory(directory, crawler_config)

   return crawler.lectures

def crawl_pdf(directory):
   # Only crawl lectures like "B-01-60erjahre-arpanet.pdf"
   return pdf_crawler.crawl_pdf(directory, lambda f: re.search("^\w-\d\d-", Path(f).stem) and f.lower().endswith(".pdf"))

if __name__ == '__main__':

   lectures = crawl_pdf("web-tech-bot/pdfs")
   from lecture_summarizer import summarize_lecture_slides
   summarize_lecture_slides(lectures)


   with open("lectures.json", "w", encoding="utf-8") as file:
      json.dump(lectures, file, cls=TagEncoder)