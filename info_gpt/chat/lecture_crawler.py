
import os

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

class Crawler():
   def __init__(self, crawl_directory=lambda dir: False, crawl_file=lambda f: f):
      self.crawl_directory = crawl_directory
      self.crawl_file = crawl_file

class Crawler_Config():
   def __init__(self, crawler) -> None:
      self.crawler = crawler

def crawl_directory(directory, crawler_config):
    # Iterate over all files in the directory
    open_list = [directory]

    count = 0
    while len(open_list) > 0:
        file = open_list.pop(0)
        count = count + 1

        if os.path.isdir(file):
            # If the directory should not be crawled directly, then add the content to the openlist
            if not(crawler_config.crawler.crawl_directory(file)):
                files = files_in_dir(file)
                for f in files:
                    open_list.append(f)
        else:
           # End the iteration if desired by the implementation
           if crawler_config.crawler.crawl_file(file):
              break
