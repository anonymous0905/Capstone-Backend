#!/usr/bin/env python
import pika, sys, os
import json
import pymongo
import torch
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import pandas as pd
import re
from transformers import pipeline
import spacy
device = torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")

nlp = spacy.load("en_core_web_sm")
try:
    embedding_model = SentenceTransformer("thenlper/gte-large").to(device)
except Exception as e:
    print(f"Error loading model: {e}")

ner_model = pipeline("ner", model="dbmdz/bert-large-cased-finetuned-conll03-english", grouped_entities=True)
def detect_names_single_case(text):
    ner_results = ner_model(text)

    processed_names = set()
    for entity in ner_results:
        if entity["entity_group"] == "PER":
            tokens = [token for token in entity["word"].replace(".", " ").split() if len(token) > 1]
            processed_names.update(tokens)

    return list(processed_names)

def anonymize_text(query):
    detected_names = detect_names_single_case(query)
    detected_names.sort(key=len, reverse=True)
    for idx, name in enumerate(detected_names):
        query = re.sub(r'\b' + re.escape(name) + r'\b', chr(65 + idx), query, flags=re.IGNORECASE)

    return query

def preprocess_text(text):
    doc = nlp(text)
    processed_words = [token.lemma_.lower() for token in doc if not token.is_stop and not token.is_punct]
    return ' '.join(processed_words)

def get_mongo_client(mongo_uri):
    try:
        client = pymongo.MongoClient(mongo_uri)
        print("Connection to MongoDB successful")
        return client
    except pymongo.errors.ConnectionFailure as e:
        print(f"Connection failed: {e}")
        return None
    
mongo_uri = "mongodb://localhost:27017"
mongo_client = get_mongo_client(mongo_uri)

if mongo_client:
    # Ingest data into MongoDB
    db = mongo_client["Capstone"]
    collection = db["Summaries"]
else:
    print("Failed to connect to MongoDB.")

def get_embedding(text: str) -> list[float]:
    if not text.strip():
        print("Attempted to get embedding for empty text.")
        return []

    embedding = embedding_model.encode(text)

    return embedding.tolist()

def setup_faiss_index(collection):
    embeddings = []
    doc_ids = []
    for doc in collection.find({}, {"embedding": 1, "_id": 1}):
        embeddings.append(doc['embedding'])
        doc_ids.append(doc['_id'])

    embedding_matrix = np.array(embeddings).astype('float32')
    index = faiss.IndexFlatL2(embedding_matrix.shape[1])
    index.add(embedding_matrix)

    return index, doc_ids

def vector_search_faiss(user_query: str, index, doc_ids, collection, top_k=4):
    query_embedding = np.array([get_embedding(user_query)], dtype='float32')
    distances, indices = index.search(query_embedding, top_k)
    results = []
    for idx, dist in zip(indices[0], distances[0]):
        doc_id = doc_ids[idx]
        doc = collection.find_one({"_id": doc_id}, {"judgment": 1, "generated_summary": 1})
        similarity_score = 1 / (1 + dist)
        doc["similarity_score"] = similarity_score
        results.append(doc)

    return results

def get_search_result_faiss(query: str, index, doc_ids, collection):
    results = vector_search_faiss(query, index, doc_ids, collection)
    search_result = {}
    i = 0
    for result in results:
        search_result[i] = f"Generated Summary: {result.get('generated_summary', 'N/A')}\n" + f"Similarity Score: {result.get('similarity_score'):.4f}\n\n"
        i+=1    
    return search_result

faiss_index, document_ids = setup_faiss_index(collection)

connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

channel.queue_declare(queue='precedent_search_health')
channel.queue_declare(queue='precedent_search_health_return')
channel.queue_declare(queue='precedent')
channel.queue_declare(queue='precedent_return')

def callback(ch, method, properties, body):
    print(" [x] Received %r" % body)
    print(" [x] Done")
    # ch.basic_ack(delivery_tag = method.delivery_tag)
    message = '200 OK'
    resp = json.dumps(message,default='str')
    channel.basic_publish(exchange='', routing_key='precedent_search_health_return', body=resp)


def callback_precedent(ch, method, properties, body):
    print(" [x] Received %r" % body)
    print(" [x] Done")
    message = json.loads(body)
    query = str(message['inputData'])
    #TODO Summarisation CALL
    query = query.replace("*", "")
    query = anonymize_text(query)
    query = preprocess_text(query)
    search_results = get_search_result_faiss(query, faiss_index, document_ids, collection)
    message = '200 OK - precedent search successful'
    resp = json.dumps(search_results)
    channel.basic_publish(exchange='', routing_key='precedent_return', body=resp)

def main():
    channel.basic_consume(queue='precedent_search_health', on_message_callback=callback, auto_ack=True)
    channel.basic_consume(queue='precedent', on_message_callback=callback_precedent, auto_ack=True)

    print(' [*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
