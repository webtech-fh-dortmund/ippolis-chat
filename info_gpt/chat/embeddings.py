from io import StringIO

from sentence_transformers import SentenceTransformer
from langchain.text_splitter import MarkdownHeaderTextSplitter

markdown_splitter = MarkdownHeaderTextSplitter(
          headers_to_split_on=[
              ("#", "Header 1"),
              ("##", "Header 2"),
              ("###", "Header 3"),
          ]
      )

class Chunker():
    def __init__(self) -> None:
       pass

    def chunk(self, data):
       for d in data:
          d["chunks"] = self.chunk_content(d["content"], d)

          # print(f"Topic: {d['topic']}")
          # print(f"{d['chunks']}")

       return data
    
    def chunk_content(self, text, meta_data):
        markdown = self.read_text_as_markdown(text)

        docs = markdown_splitter.split_text(markdown) # returns list of langchain_core.documents.base.Document

        # TODO maybe handle parent chunks (e.g. headers) differently - like retain the parent-child hierarchy

        id = 0
        chunks = []
        for d in docs:
          # Differ between text and langchain_core.documents.base.Document, so only strings are contained in the end
          chunk_content = d if isinstance(d, str) else d.page_content
          chunks.append({"id": id, "topic": meta_data["topic"], "meta_data_id": meta_data["id"], "content": chunk_content})
          id = id + 1

        return chunks

    def read_text_as_markdown(self, text):
        file_like_io = StringIO(text)
        lines = ""
        i = 0
        empty_lines = 0
        for line in file_like_io:
           if len(line.strip()) == 0:
              empty_lines = empty_lines + 1
           else:
              # After a newline or at the first line of text start a new paragraph
              if empty_lines > 0 or lines == "":
                 lines = lines + f"\n# H {str(i)}\n{line.strip()}\n"
                 i = i +1
              else:
                 lines = lines + line.strip()
              empty_lines = 0
        return lines

class Embedder():
    def __init__(self) -> None:
       self.encoder_model = SentenceTransformer('all-MiniLM-L6-v2')

    def embed_user_query(self, user_query):
       return self.encoder_model.encode([user_query])

    def embed(self, data):
       all_embeddings = []

       for d in data:
          embeddings = self.embed_chunks(d["chunks"])

          d["embeddings"] = embeddings

         #  all_embeddings.append({"src_id": d["id"], "embeddings": embeddings})

          chunks = []
          for c in d["chunks"]:
             chunks.append((c["content"], c["topic"]))

          article={}
          article['embeddings'] = []
         #  article['doc'] = doc
          for (chunk, embedding) in zip(chunks, embeddings):
            # article['embeddings'].append(Embedding(chunk, embedding.tolist(), len(chunk), doc))

            article['embeddings'].append({"source": chunk[0], "embedding": embedding.tolist(), "sourcelength": len(chunk), "id": d["id"], "topic": chunk[1]})

            # item = {}
            # item['source'] = chunk
            # item['embedding'] = embedding.tolist()  # Convert NumPy array to list
            # item['sourcelength'] = len(chunk)
            # article['embeddings'].append(item)

          # Sort the embeddings based on id.
          article['embeddings'].sort(key=lambda emb: emb["id"], reverse=False)

          all_embeddings.append(article)

       return data, all_embeddings
    
    def embed_chunks(self, chunks):
      # chunk_contents = [c["content"] for c in chunks]
      chunk_contents = []
      for c in chunks:
         chunk_contents.append(c["content"])

      embeddings = self.encoder_model.encode(chunk_contents) # Returns a NumPy array
      return embeddings
    



