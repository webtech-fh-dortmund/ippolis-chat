
import os
import json

def write_json_file(path, obj):
   with open(path, "w", encoding="utf-8") as f:
      json.dump(obj, f, ensure_ascii=False)

def read_json_file(path):
   with open(path, "r", encoding="utf-8") as file:
      js = json.load(file)
   return js

def files_in_dir(root_dir, filetype_filter=[]):
  # List all files in a directory, include only those, that match the filter
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

def iterate_directory(root_dir, filetype_filter=[], dir_filter=lambda dir: False):
   # Iterate over all files in the directory
   open_list = [root_dir]

   paths = []

   count = 0
   while len(open_list) > 0:
         file = open_list.pop(0)
         # print(f"ol: {file}")
         count = count + 1

         for f in os.listdir(file):
            # print(f)
            f = file+"/"+f
            if os.path.isfile(f):
               if (len(filetype_filter) == 0 or len([ft for ft in filetype_filter if (f).endswith(ft)]) > 0):
                  paths.append(f)
            else:
               if not(dir_filter(f)):
                  open_list.append(f)
   return paths
