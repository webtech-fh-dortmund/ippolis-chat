
from pathlib import Path

import lecture_crawler
import pymupdf

def crawl_lecture(file, lectures):
   slides = []
   lecture = {"name": Path(file).stem, "slides": slides}
   lectures.append(lecture)

   doc = pymupdf.open(file) # open a document
   page_nr = 0
   for page in doc: # iterate the document pages
      text = page.get_text() # get plain text encoded as UTF-8
      # print(text)
      page_nr = page_nr +1
      slides.append({"header": "", "text": text, "links": [], "videos": [], "images": [], "tables": [], "page": page_nr})

def crawl_pdf(directory, file_filter=lambda f: True):

   def crawl_directory(dir):
      print(f"dir: {dir}")

      return False

   def crawl_file(f):
      print(f"file: {f}")

      if file_filter(f):
         print("\t Crawled file")
         
         crawl_lecture(f, crawler.lectures)
         # TODO for testing only
         # End the crawling on the first matching pdf
         # return True
      return False

   crawler = lecture_crawler.Crawler(crawl_directory, crawl_file)
   crawler.lectures = []

   crawler_config = lecture_crawler.Crawler_Config(crawler)

   lecture_crawler.crawl_directory(directory, crawler_config)

   return crawler.lectures
