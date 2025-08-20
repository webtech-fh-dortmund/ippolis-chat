
import re
from pathlib import Path
from datetime import datetime

from ollama_rag import call_ollama

def summarize_lecture_slides(lectures):
    # Workaround for a dummy App_Config object
    app_config = lambda: None
    app_config.ollama_ip = "http://192.168.0.253:11434"
    app_config.model = "llama3.1:8b-instruct-q8_0"

    system_prompt = "Befolge genau die Anweisungen."


    for lecture in lectures:
        lecture_name = lecture["name"]

        slides = lecture["slides"]
        for slide in slides:
            text = slide["text"]
            user_query = f"Strukturiere den folgenden Text: {text}"

            summary = call_ollama(user_query, system_prompt, app_config)

            # Remove the header from the summary
            summary = re.sub("\*\*.*?\*\*", "", summary, 1)

            header = text.split("\n")[0]

            print("old text:")
            print(text)
            print("\n")
            print("new:")
            print (summary)
            print("\n")

            slide["header"] = header
            slide["text"] = summary

            # Break after the first slide
            # return

        # Break after the first lecture
        # return
