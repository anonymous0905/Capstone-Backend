
#!/usr/bin/env python
import pika, sys, os
import json
import requests
from pyexpat.errors import messages

connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

channel.queue_declare(queue='summarization_health')
channel.queue_declare(queue='summarization_health_return')
channel.queue_declare(queue='summary')
channel.queue_declare(queue='summary_return')

def callback(ch, method, properties, body):
    print(" [x] Received %r" % body)
    print(" [x] Done")
    #extract the message from the body

    # ch.basic_ack(delivery_tag = method.delivery_tag)
    message = '200 OK'
    resp = json.dumps(message,default='str')
    channel.basic_publish(exchange='', routing_key='summarization_health_return', body=resp)


def callback_summary(ch, method, properties, body):
    print(" [x] Received %r" % body)
    print(" [x] Done")
    message = json.loads(body)
    text = message['inputData']
    #print(text)

    API_TOKEN = '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'
    API_URL = "https://mz4m63dt514ihp7b.us-east-1.aws.endpoints.huggingface.cloud"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }

    def query(payload):
        response = requests.post(API_URL, headers=headers, json=payload)
        return response.json()

    output = query({
        "inputs": text,
        "parameters": {}
    })
    #TODO: Implement summarization logic here
    #message = '200 OK - Summary generated successfully'
    print(output)
    resp = json.dumps(output,default='str')
    channel.basic_publish(exchange='', routing_key='summary_return', body=resp)

def main():
    channel.basic_consume(queue='summarization_health', on_message_callback=callback, auto_ack=True)
    channel.basic_consume(queue='summary', on_message_callback=callback_summary, auto_ack=True)
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
