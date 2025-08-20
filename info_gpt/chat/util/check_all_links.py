
import os
import re
import urllib.request

def files_in_dir(root_dir, filetype_filter=[]):
  paths = []
  for file in os.listdir(root_dir):
    # If either any filetype match
    for ft in filetype_filter:
       if file.endswith(ft):
          paths.append(file)
    # Or if none are specified, then add the file
    if len(filetype_filter) == 0:
      paths.append(file)
  return paths

def read_file(url):
    with open(url, encoding="utf-8") as f:
        lines = f.read()
    return lines

def get_all_urls(root_dir):
    # Dictionary of link:[file] pairs, storing a link and all files where it appears
    all_links = {}

    files = files_in_dir(root_dir, ["txt"])
    for file in files:
        content = read_file(root_dir+"/"+file)
        
        # Good regexp, but also allows "." at the end of urls
        match = re.findall("https?://[-a-zA-Z0-9@:%._\\+~#=]{2,256}\\.[a-z]{2,6}\\b[-a-zA-Z0-9@:%_\\+.~#?&//=]*", content)
        
        # Remove all "." at the end of the urls
        match = [m[0:len(m)-1] if m.endswith(".") else m for m in match]

        # Either add the link's file to all_links
        for link in match:
            if link in all_links:
                all_links[link].append(file)
            else:
                all_links[link] = [file]

    return all_links

def url_available(link):
    try:
        status_code = urllib.request.urlopen(link).getcode()
    except Exception as err:
       if type(err) == urllib.error.HTTPError:
          return (False, err.code)
       print(f"Error: {err} - Link unavailable: {link}")
       return (False, -1)

    # The website is available if it either responded with "200 OK" or not with "404 Not Found"
    available = status_code == 200 or status_code != 404

    if not(available):
       print(f"HTTP Status-Code: {status_code}")

    return (available, status_code)

def check_if_all_urls_available_in_files_in(root_dir):
    print("check_if_all_urls_available_in_files_in(): Checking all links, this might take a while")

    all_links = get_all_urls(root_dir)

    unavailable_links = {}

    for link in all_links:

       available, status_code = url_available(link)

       if not(available):
          print(f"Unavailable: {link}")
          print(f"Status code: {status_code}")
          print(f"Used in files: {all_links[link]}")
          unavailable_links[link] = {"status_code": status_code, "files": all_links[link]}

    return {"unavailable urls": unavailable_links}
