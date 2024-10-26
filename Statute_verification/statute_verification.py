
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

tokenizer = AutoTokenizer.from_pretrained("law-ai/InLegalBERT")
dataset = pd.read_json("train.jsonl", lines=True)

mlb = MultiLabelBinarizer()
labels = mlb.fit_transform(dataset['labels'])
labels = torch.tensor(labels, dtype=torch.float32)
model = AutoModelForSequenceClassification.from_pretrained("law-ai/InLegalBERT", num_labels=len(mlb.classes_))
model.load_state_dict(torch.load("model_epoch_weighted_20.pt"))

def predict_sections(text, model, tokenizer, mlb):
    model.eval()
    inputs = tokenizer([text], padding=True, truncation=True, return_tensors="pt")
    with torch.no_grad():
        outputs = model(input_ids=inputs['input_ids'], attention_mask=inputs['attention_mask'])
        logits = outputs.logits
        predictions = torch.sigmoid(logits) > 0.1
    predicted_labels = mlb.inverse_transform(predictions.cpu().numpy())
    print(type(predicted_labels))
    print(predicted_labels)
    return predicted_labels


connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

channel.queue_declare(queue='statute_verification_health')
channel.queue_declare(queue='statute_verification_health_return')
channel.queue_declare(queue='statute')
channel.queue_declare(queue='statute_return')

def callback(ch, method, properties, body):
    print(" [x] Received %r" % body)
    print(" [x] Done")
    # ch.basic_ack(delivery_tag = method.delivery_tag)
    message = '200 OK'
    resp = json.dumps(message,default='str')
    channel.basic_publish(exchange='', routing_key='statute_verification_health_return', body=resp)

def callback_statute(ch, method, properties, body):
    print(" [x] Received %r" % body)
    print(" [x] Done")
    message = json.loads(body)
    print(message)
    text = message['inputData']
    predicted_sections = predict_sections(text, model, tokenizer, mlb)
    #TODO: Implement statute verification logic here
    message = '200 OK - Statute verified successfully'
    resp = json.dumps(predicted_sections,default='str')
    channel.basic_publish(exchange='', routing_key='statute_return', body=resp)

def main():
    channel.basic_consume(queue='statute_verification_health', on_message_callback=callback, auto_ack=True)
    channel.basic_consume(queue='statute', on_message_callback=callback_statute, auto_ack=True)

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
