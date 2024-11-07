#!/usr/bin/env python
import pika, sys, os
import json
import torch
from transformers import AutoTokenizer
import pandas as pd
from sklearn.preprocessing import MultiLabelBinarizer
from transformers import AutoModelForSequenceClassification
from sklearn.utils.class_weight import compute_class_weight
import numpy as np

# Set device to MPS if available
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

tokenizer = AutoTokenizer.from_pretrained("law-ai/InLegalBERT")
dataset = pd.read_json("train.jsonl", lines=True)

mlb = MultiLabelBinarizer()
labels = mlb.fit_transform(dataset['labels'])
labels = torch.tensor(labels, dtype=torch.float32)
model = AutoModelForSequenceClassification.from_pretrained("law-ai/InLegalBERT", num_labels=len(mlb.classes_))

# Load model weights and move model to MPS
model.load_state_dict(torch.load("model_epoch_weighted_29.pt", map_location=torch.device('cpu')))
model.to(device)

with open('secs.json', 'r') as file:
    secs_data = json.load(file)

def predict_sections(text, model, tokenizer, mlb):
    model.eval()

    # Tokenize input text
    inputs = tokenizer([text], padding=True, truncation=True, return_tensors="pt").to(device)

    with torch.no_grad():
        # Get model outputs
        outputs = model(input_ids=inputs['input_ids'], attention_mask=inputs['attention_mask'])
        logits = outputs.logits

        # Apply sigmoid and threshold to get predictions
        predictions = torch.sigmoid(logits) > 0.1

    # Inverse transform to get predicted labels
    predicted_labels = mlb.inverse_transform(predictions.cpu().numpy())

    # Flatten the predicted labels since inverse_transform returns a list of lists
    predicted_labels = [item for sublist in predicted_labels for item in sublist]

    # Find matching sections in secs.json
    matching_sections = []
    for section in secs_data['data']:
        for label in predicted_labels:
            if label in section['id']:
                matching_sections.append({
                    "section": section['id'],
                    "text": section['text'][0]  # Get the first text entry
                })
    print(matching_sections)
    # Output the matching sections and their corresponding texts
    return matching_sections

connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

channel.queue_declare(queue='statute_verification_health')
channel.queue_declare(queue='statute_verification_health_return')
channel.queue_declare(queue='statute')
channel.queue_declare(queue='statute_return')

def callback(ch, method, properties, body):
    print(" [x] Received %r" % body)
    print(" [x] Done")
    message = '200 OK'
    resp = json.dumps(message, default='str')
    channel.basic_publish(exchange='', routing_key='statute_verification_health_return', body=resp)


def callback_statute(ch, method, properties, body):
    try:
        message = json.loads(body)
        text = message['inputData']
    except json.JSONDecodeError:
        print(" [x] Error decoding message")
        response = json.dumps({"error": "Invalid JSON format"})
        ch.basic_publish(exchange='', routing_key='statute_return', body=response)
        ch.basic_ack(delivery_tag=method.delivery_tag)  # Acknowledge error message processing
        return

    # Try processing the statute and handling the result
    predicted_sections = predict_sections(text, model, tokenizer, mlb)
    print(predicted_sections)

    response_message = '200 OK - Statute verified successfully'
    response_data = {
        'status': response_message,
        'predictedSections': predicted_sections
    }
    resp = json.dumps(response_data, default=str)

    ch.basic_publish(exchange='', routing_key='statute_return', body=resp)

    # Acknowledge successful processing only after publishing response
    ch.basic_ack(delivery_tag=method.delivery_tag)
    print(" [x] Done")

def main():
    # Use auto_ack=False to manually acknowledge messages
    channel.basic_consume(queue='statute_verification_health', on_message_callback=callback, auto_ack=False)
    channel.basic_consume(queue='statute', on_message_callback=callback_statute, auto_ack=False)

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
