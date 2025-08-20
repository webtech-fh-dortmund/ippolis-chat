
import json
from requests import post as requests_post

# Imports for image handling
from PIL import Image
import urllib.request
from io import BytesIO
from binascii import b2a_base64

def send_images_ollama(images, user_query, chat_model, ollama_ip="http://172.22.160.12:11434", streaming=False):

    api_endpoint = "/api/generate"

    stream_config = {
                    'model': chat_model, "streaming": streaming,
                    "prompt": user_query,
                    "images": images,
                    "options": {
                        "temperature": 0.0,
                        "seed": 123
                    }
        }
    
    try:
        answer = ""

        i = 0
        with requests_post(ollama_ip+api_endpoint, json=stream_config, stream=streaming) as resp:

            resp.raise_for_status()

            body = None
            for line in resp.iter_lines():

                # Encode the received bytes as string, ignoring unicode characters that can't be decoded
                body = json.loads(line.decode("utf-8", "ignore"))
                
                if 'error' in body:
                    raise Exception(body['error'])

                # Differ between "chat" and "generate" API
                if api_endpoint == "/api/chat":
                    response_part = body.get('message', '')["content"]
                elif api_endpoint == "/api/generate":
                    response_part = body.get('response', '')

                answer = answer + str(response_part)

                # i = i +1
                # if i % 5 == 0:
                #     print(answer)
                
                done = body.get('done', False)

                if done:
                    break


            if body == None:
                return answer

            return answer

    except Exception as err:
        raise err

def open_image(image_path, width=-1, height=-1):
    image = Image.open(image_path)
    return open_img(image, width, height)

def open_img(image, width=-1, height=-1):
    if width == -1 or height == -1:
        return image
    
    old_width, old_height = image.size

    # Don't upscale the image if not necessary
    if old_width < width and old_height < height:
        width = old_width
        height = old_height
    else:
        if width/old_width < height/old_height:
            height = old_height * (width/old_width)
            # Increase size if too small
            if height < old_height/2:
                height = height * 1.5
                width = width * 1.5
        else:
            width = int(old_width * (height/old_height))
            # Increase size if too small
            if width < old_width/2:
                height = height * 1.5
                width = width * 1.5
        print(f"{old_width}, {old_height} to {width}, {height}")

    # Resize the image to a size manageable by the LLM
    # e.g. for Llava:7b 672x672, 336x1344, 1344x336
    image = image.resize((int(width), int(height)))
    
    # Convert the Pillow image to a hex data string
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    # Convert the hex data to base64
    src = b2a_base64(buffer.getvalue())
    # Convert the image to string and remove the leading "b'" and trailing "\n'"
    src = str(src)
    src = src[2:len(src)-3]

    return src

def scale_image(img_data, width, height):
    # Retrieve the data from the data URI
    response = urllib.request.urlopen(img_data)
    # Convert it to a Pillow image
    image = Image.open(response)
    # Resize the image to a size manageable by the LLM
    # e.g. for Llava:7b 672x672, 336x1344, 1344x336
    image = image.resize((width, height))
    
    # Convert the Pillow image to a hex data string
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    # Convert the hex data to base64
    src = b2a_base64(buffer.getvalue())
    # Convert the image to string and remove the leading "b'" and trailing "\n'"
    src = str(src)
    src = src[2:len(src)-3]

    return src
