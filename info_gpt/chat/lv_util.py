
import json
from ollama_rag import RAG


def best_matches(user_query, app_config, knowledge_base, embeddings):

    # Embed the user's question
    question_embedding = knowledge_base.embedder.embed_user_query(user_query)

    # Perform KNN search to find the best matches
    best_matches = RAG().knn_search(question_embedding, embeddings)

    return best_matches

def custom_metadata(user_query, app_config, knowledge_base, metadata, matches_to_find = 10, final_matches = 3):

    # Embed the user's question
    question_embedding = knowledge_base.embedder.embed_user_query(user_query)

    # Perform KNN search to find the best matches
    # Index, source_text, topic, distance
    # Always find a fixed number of matches via KNN and reduce the number later via a Reranker (matches_to_find)
    best_matches = RAG().knn_search(question_embedding, knowledge_base.all_embeddings, min(matches_to_find, len(knowledge_base.all_embeddings[0]["embeddings"])))
    

    sources = [item['source'] for article in knowledge_base.all_embeddings for item in article['embeddings']]
    lectures = [item['lecture'] for article in knowledge_base.all_embeddings for item in article['embeddings']]
    pages = [item['page'] for article in knowledge_base.all_embeddings for item in article['embeddings']]
    headers = [item['header'] for article in knowledge_base.all_embeddings for item in article['embeddings']]

    # {lecture, page, source, topic, distance}
    best_matches = [{"lecture": lectures[best_matches[i][0]], "page": pages[best_matches[i][0]], "header": headers[best_matches[i][0]], "src": sources[best_matches[i][0]], 
                     "topic": best_matches[i][2], "distance": best_matches[i][3]} for i in range(len(best_matches))]

    # Now sort based on lecture and page. This will be the secondary sort, e.g. first on KNN distance, then on lecture and page
    best_matches.sort(key=lambda match: match["page"], reverse=False)
    best_matches.sort(key=lambda match: match["lecture"], reverse=False)
    # Sort the best matches based on distance (ascending). This will be the secondary sort.
    best_matches.sort(key=lambda match: match["distance"], reverse=False)

    # Reduce best matches down to e.g. 3
    best_matches = best_matches[0:final_matches]

    metadata = []

    for bm in best_matches:
        entry = {}
        metadata.append(entry)
        entry["url"] = f"No ilias ID found for lecture: {bm['lecture']}"

        entry["Vorlesung"] = bm["lecture"]
        entry["Seite"] = bm["page"]
        entry["KNN-Distanz"] = bm["distance"]
        entry["Inhalt"] = bm["src"]
        entry["Titel"] = bm["header"]

    return metadata

def log_metadata(metadata):
    metadata = json.loads(metadata)
    return [f"[{entry['Vorlesung']}, S. {entry['Seite']}, {entry['Titel']}]" for entry in metadata]
