#!/usr/bin/env python
import pika
import sys
import os
import json
import pymongo
import torch
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import re
from transformers import pipeline
import spacy
from flask import g

# Set up device
device = torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")

# Load NLP models
nlp = spacy.load("en_core_web_sm")
try:
    embedding_model = SentenceTransformer("thenlper/gte-large").to(device)
except Exception as e:
    print(f"Error loading model: {e}")

ner_model = pipeline("ner", model="dbmdz/bert-large-cased-finetuned-conll03-english", grouped_entities=True)

# MongoDB setup
mongo_uri = "mongodb://localhost:27017"
mongo_client = pymongo.MongoClient(mongo_uri)
db = mongo_client["Capstone"]
collection = db["Summaries"]

# Helper functions
def detect_names_single_case(text):
    ner_results = ner_model(text)
    processed_names = {token for entity in ner_results if entity["entity_group"] == "PER"
                       for token in entity["word"].replace(".", " ").split() if len(token) > 1}
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

def get_embedding(text):
    if not text.strip():
        print("Attempted to get embedding for empty text.")
        return []
    embedding = embedding_model.encode(text)
    return embedding.tolist()

def setup_faiss_index(collection):
    embeddings = [doc['embedding'] for doc in collection.find({}, {"embedding": 1, "_id": 1})]
    doc_ids = [doc['_id'] for doc in collection.find({}, {"_id": 1})]
    embedding_matrix = np.array(embeddings).astype('float32')
    index = faiss.IndexFlatL2(embedding_matrix.shape[1])
    index.add(embedding_matrix)
    return index, doc_ids

def vector_search_faiss(user_query, index, doc_ids, collection, top_k=4):
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

def get_search_result_faiss(query, index, doc_ids, collection):
    results = vector_search_faiss(query, index, doc_ids, collection)
    return {i: f"Generated Summary: {result.get('generated_summary', 'N/A')}\n" +
               f"Similarity Score: {result.get('similarity_score'):.4f}\n\n"
            for i, result in enumerate(results)}

# FAISS index setup
faiss_index, document_ids = setup_faiss_index(collection)

# RabbitMQ connection
connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost', heartbeat=8000))
channel = connection.channel()
channel.queue_declare(queue='precedent')
channel.queue_declare(queue='summary')
channel.queue_declare(queue='summary_return')
channel.queue_declare(queue='precedent_return')

# Callback function with synchronous basic_get
def callback_precedent(ch, method, properties, body):
    print(" [x] Received %r" % body)

    # Publish message to summary queue
    channel.basic_publish(exchange='', routing_key='summary', body=body)
    method_frame, header_frame, response_body = channel.basic_get(queue='summary_return', auto_ack=True)
    if method_frame:
        response_body = response_body.decode()
        data = json.loads(response_body)
        summary_result = json.dumps(data, default=str)
    else:
        summary_result = json.dumps({'error': 'Summary Not Found'})

    # Process the summary result
    parsed_data = json.loads(summary_result)
    print(parsed_data)
    query = parsed_data.get("summary", "").replace("*", "")
    query = anonymize_text(query)
    query = preprocess_text(query)

    # Perform vector search with FAISS
    search_results = get_search_result_faiss(query, faiss_index, document_ids, collection)
    response_message = json.dumps(search_results)

    # Publish the search results to the precedent_return queue
    channel.basic_publish(exchange='', routing_key='precedent_return', body=response_message)
    print(" [x] Precedent search completed and response sent.")

# Main function to consume messages
def main():
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