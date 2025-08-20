import json
from datetime import datetime
from requests import post as requests_post

from numpy import array as np_array
from sklearn.neighbors import NearestNeighbors
from stundenplan_crawler import transform_data, embedding_search

def determine_topic(user_query, all_topics, app_config):
    system_prompt = "Antworte nur mit einem der folgenden Begriffe. Wenn kein Wort exakt passt, dann antworte 'Thema unbekannt':"

    themes = ""
    for f in all_topics:
        themes = themes + f + ", "
    themes = themes[0:-2] # Remove the last ", "

    system_prompt = system_prompt + themes

    return call_ollama(user_query, system_prompt, app_config)

def stream_reply(string, step = 5):
    """
    Should be used like this:\n
    \tfor s in stream_reply(reply):
    \t\tyield s
    """
    i = 0
    for i in range(0, len(string), step):
        yield (False, string[i:i+step])
    yield (True, string)

class RAG():
    def __init__(self) -> None:
        pass

    def rag(self, user_query, system_prompt, knowledge_base, app_config, k=10):

        if app_config.custom_pre_RAG != None:
            user_query = app_config.custom_pre_RAG(user_query, app_config, knowledge_base)
        
        metadata = [] # [{index, source}]

        user_query_topic = ""
        if app_config.enable_topic_detection:
            user_query_topic = determine_topic(user_query, knowledge_base.all_topics, app_config)
            print(f"user_query_topic {user_query_topic}")

        # TODO if custom logic for specific topics triggers, then still return system_prompt, metadata
        if app_config.chatbot_id == "Info-GPT":
            pass

        # Embed the user's question
        question_embedding = knowledge_base.embedder.embed_user_query(user_query)

        # Always find a fixed number of matches via KNN and reduce the number later via a Reranker
        matches_to_find = 30

        # Perform KNN search to find the best matches
        best_matches = self.knn_search(question_embedding, knowledge_base.all_embeddings, matches_to_find)

        ###########################
        ####### Reranking #########
        ###########################

        # Sort the best matches based on distance (ascending). This will be the secondary sort.
        best_matches.sort(key=lambda match: match[3], reverse=False)
        # Now sort based on if the theme matches the theme of the user query. This will be the primary sort, e.g. first on matching theme, then on KNN distance
        best_matches.sort(key=lambda match: match[2] == user_query_topic, reverse=True)

        # TODO Remove all matches that are below a certain threshold (e.g. only keep the best 80%)
        

        # print(f"best_matches: {best_matches}")

        # Reduce the number of matches to the desired k
        best_matches = best_matches[0 : k]
        
        if app_config.chatbot_id == "Info-GPT":
            # TODO add the mentoring_info to the end of best_matches
            # TODO how to handle english and how to integrate this better into the pipeline?
            mentoring_info = ("Du kannst dich aber auch jederzeit mit persönlichen Anliegen oder Problemen an das Mentoring wenden. "
                              "Dazu schaust du am besten im Raum B.E.03, 04 oder 05 vorbei.")
            pass

        # print(f"best_matches reranked: {best_matches}")

        ###########################
        ###########################
        ###########################

        rag_knowledge=" "
        # rag_knowledge="Knowledge Base: ["
        for i, (index, source_text, topic, distance) in enumerate(best_matches, start=1):
            rag_knowledge += f"{source_text}"
            if i < len(best_matches):
                rag_knowledge += "\n\n"

            metadata.append({"index": index, "source": source_text})
        rag_knowledge += "]"

        # print(f"RAG: {rag_knowledge}")

        system_prompt = system_prompt + rag_knowledge

        # Overwrite the metadata if configured so
        if app_config.custom_metadata != None:
            metadata = app_config.custom_metadata(user_query, app_config, knowledge_base, metadata)

        if app_config.custom_post_RAG != None:
            user_query = app_config.custom_post_RAG(user_query, app_config, knowledge_base)

        return system_prompt, metadata

    # Perform K-nearest neighbors (KNN) search
    def knn_search(self, question_embedding, embeddings, k=10):
        if type(embeddings[0]) == dict:
            X = np_array([item['embedding'] for article in embeddings for item in article['embeddings']])
            # X = np_array([item.embedding for article in embeddings for item in article['embeddings']])
            # X = np_array([article['embeddings'] for article in embeddings])
            # X = np_array([item['embeddings'] for article in embeddings for item in article])

            source_texts = [item['source'] for article in embeddings for item in article['embeddings']]
            # source_texts = [item.source for article in embeddings for item in article['embeddings']]
            # source_texts = [article['content'] for article in embeddings]
            # source_texts = [item['content'] for article in embeddings for item in article]
            
            topics = [item['topic'] for article in embeddings for item in article['embeddings']]
        else:
            X = np_array(embeddings)

        # Clamp k down to the maximum number of embeddings
        k = min(k, len(X))
        # Fit a KNN model on the embeddings
        knn = NearestNeighbors(n_neighbors=k, metric='cosine')
        knn.fit(X)
        
        # Find the indices and distances of the k-nearest neighbors
        distances, indices = knn.kneighbors(question_embedding, n_neighbors=k)
        
        if type(embeddings[0]) == dict:
            # Get the indices and source texts of the best matches
            # Convert numpy int64 to python int via item()
            best_matches = [(indices[0][i].item(), source_texts[indices[0][i]], topics[indices[0][i]], distances[0][i]) for i in range(k)]
        else:
            # Get the indices and distances of the best matches
            best_matches = [(indices[0][i].item(), distances[0][i]) for i in range(k)]

        return best_matches

def send_msg_ollama(data, botPerformance, context, language, app_config, reservation, knowledge_base, streaming=True):

    botPerformance = int(botPerformance)

    print(f"send_msg_ollama(): botPerformance: {botPerformance}")

    user_query = data["data"]
    
    # Remove older messages that exceed the context length. Don't remove any if value == -1
    if app_config.context_length != -1:
        while len(context[0])-1 > app_config.context_length * 2:
            del context[0][1]

    # Update the context
    context[0].append({
                    "role": "user",
                    "content": user_query
                    })
    
    chat_model = app_config.model

    if (app_config.chatbot_id == "Info-GPT" or app_config.chatbot_id == "FB9-GPT") and app_config.enable_topic_detection:
        if language == "de":
            difficult_topics =  ["Psychische Probleme", "Studienabbruch", "Schwierige Themen",  "Persönliche Probleme"]
        else:
            difficult_topics = ["psychological problems", "drop-out", "difficult topic", "very personal topic"]
        user_query_topic = determine_topic(user_query, knowledge_base.all_topics.union(set(difficult_topics)), app_config)
        if user_query_topic in difficult_topics:
            print(f"Difficult Topic: {user_query_topic}")
            replies = {
                "Info-GPT": {"de": ("Ich bin nur eine Künstliche Intelligenz und kann dir leider nicht weiterhelfen 🙁. "
                                    "Wenn du mit einem Menschen darüber reden möchtest, ist das Mentoring-Team immer für dich da. "
                                    "Schau einfach spontan im Raum B.E.03, 04 oder 05 vorbei"), 
                             "en": ("I am just an artificial intelligence and can not help you 🙁. "
                                    "If you want to talk about it with a human, the mentoring-team is always there for you. "
                                    "You can visit room B.E.03, 04 or 05 anytime")},
                difficult_topics[0]: {"de": ("Ich bin nur eine Künstliche Intelligenz und kann dir leider nicht weiterhelfen 🙁. "
                                    "Wenn du mit einem Menschen darüber reden möchtest, kann dir die psychologische Studienberatung vlt. weiterhelfen. "),
                             "en": ("I am just an artificial intelligence and can not help you 🙁. "
                                    "If you want to talk about it with a human, the psychological study counseling may be able to help you. ")}
            }

            # Either match the difficult topic, if there is a custom reply or use the default answer for each chatbot
            if user_query_topic in replies:
                reply = replies[user_query_topic][language]
            else:
                reply = replies[app_config.chatbot_id][language]

            for s in stream_reply(reply):
                yield s
            # Add the answer to the context
            context[0].append({
                "role": "assistant",
                "content": reply
                })
            return

    # If the bot performance is set to be fast, then disable the context awareness (by removing all previous parts of the conversation)
    if botPerformance == "fastest" or botPerformance == "fast" or botPerformance < 2:
        context[0] = [[]]
    # Choose the amount of best matching chunks to find for RAG
    best_rag_matches = app_config.best_rag_matches
    # And the Ollama API endpoint
    api_endpoint = "/api/chat"
    # if botPerformance == "fastest" or botPerformance == 0:
    #     best_rag_matches = 5
    #     api_endpoint = "/api/generate"
    # if botPerformance == "good" or botPerformance == 3:
    #     # TODO implement
    #     pass
    # if botPerformance == "best" or botPerformance == 4:
    #     best_rag_matches = 15

    system_prompt = app_config.chat_system_prompt
    if app_config.enable_rag:
        system_prompt, metadata = RAG().rag(user_query, system_prompt, knowledge_base, app_config, best_rag_matches)
    else:
        system_prompt = system_prompt
        metadata =[]

    if app_config.chatbot_id == "Webster" and "search_only" in data:
        yield (True, "Answer", json.dumps(metadata))
        return

    if app_config.answer_only_with_metadata:
        yield(False, "")
        yield (True, "", json.dumps(metadata))
        return


    if language == "de":
        system_prompt = "Antworte immer auf Deutsch. "+system_prompt
    else:
        system_prompt = "Always answer in english. "+system_prompt

    if app_config.enable_stundenplan_crawler:
        system_prompt = embedding_search(transform_data(), user_query, RAG(), None, attribute_search=["name", "courseType", "Dozent*in Nachname", "Wochentag", "Studiengänge"])

    # Update the context
    # It is yet to be discovered if "role": "user" or "system" works better for most use-cases.
    context[0][0] = {
                "role": "system",
                "content": system_prompt
                }
    
    # print(f"send_msg_ollama() context: {context[0]}")

    stream_config = {
                    'model': chat_model, "streaming": streaming,
                    "options": {
                        "temperature": 0.0,
                        "seed": 123
                    }
        }
    if api_endpoint == "/api/chat":
        stream_config["messages"] = context[0]
    elif api_endpoint == "/api/generate":
        stream_config["prompt"] = user_query
        stream_config["system"] = system_prompt
        stream_config["context"] = []

    try:
        answer = ""
        print("Message processing started: "+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'))

        with requests_post(app_config.ollama_ip+api_endpoint, json=stream_config, stream=streaming) as resp:

            print("Message processing done: "+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'))

            resp.raise_for_status()

            # If the reservation has been stopped meanwhile, then also stop Ollama
            if not(reservation.ongoing):
                # Close the connection rather than reading through the streamed response, which stops Ollama from continuing to generate
                resp.close()

            body = None
            for line in resp.iter_lines():

                # If the reservation has been stopped meanwhile, then also stop Ollama
                if not(reservation.ongoing):
                    # Close the connection rather than reading through the streamed response, which stops Ollama from continuing to generate
                    resp.close()
                    break

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
                
                done = body.get('done', False)

                if done:
                    # If the request is done, also send the metadata
                    yield (done, response_part, json.dumps(metadata))

                    # Overwrite the old context
                    # Only for the "generate" API
                    # context[0] = body['context']

                    # Add the answer to the context
                    context[0].append({
                        "role": "assistant",
                        "content": answer
                        })
                    break

                # Send the next part of the response
                yield (done, response_part)


            if body == None:
                print("send_msg_ollama(): Stopped request before generating")
                yield (True, "Stopped request before generating")
                return

            print("Message sending done: "+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    except Exception as err:
        # Using yield informs the user of the exception, while return doesn't
        yield (False, " Ein unerwarteter Fehler ist leider aufgetreten.")
        yield (True, "")
        raise err

def call_ollama(user_query, system_prompt, app_config) -> str:

    chat_model = app_config.model

    stream_config = {
                    "model": chat_model,
                    "prompt": user_query,
                    "system": system_prompt,
                    "streaming": False,
                    "options": {
                        "temperature": 0.0,
                        "seed": 123
                    }
        }

    answer = ""
    try:

        with requests_post(app_config.ollama_ip+"/api/generate", json=stream_config, stream=False) as resp:

            resp.raise_for_status()

            for line in resp.iter_lines():
                # Encode the received bytes as string, ignoring unicode characters that can't be decoded
                body = json.loads(line.decode("utf-8", "ignore"))
                
                if 'error' in body:
                    raise Exception(body['error'])

                response_part = body.get('response', '')

                answer = answer + str(response_part)
                
                done = body.get('done', False)

                if done:
                    break

    except Exception as err:
        # Using yield informs the user of the exception, while return doesn't
        print("Ein unerwarteter Fehler ist leider aufgetreten.")
        raise err
    finally:
        return answer

def load_model_into_memory(app_config):
    if app_config.testing_mode:
        return
    
    stream_config = {
                    "model": app_config.model
        }
    try:
        with requests_post(app_config.ollama_ip+"/api/generate", json=stream_config) as resp:
            resp.raise_for_status()

            for line in resp.iter_lines():
                print("Loaded model into memory")
                break
    except Exception as err:
        print("Error: Could not load model into memory.")
        raise err