
#!/usr/bin/env python
import pika, sys, os
import json

from scipy.stats import false_discovery_control

connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost', heartbeat=8000))
channel = connection.channel()
#queue to send and receive health check messages from producer
channel.queue_declare(queue='health_check')
channel.queue_declare(queue='health_check_return')
#queue to send and receive messages from contract module
channel.queue_declare(queue='contract_health')
channel.queue_declare(queue='contract_health_return ')
#queue to send and receive messages from OCR module
channel.queue_declare(queue='ocr_health')
channel.queue_declare(queue='ocr_health_return')
#queue to send and receive messages from Precedent Search module
channel.queue_declare(queue='precedent_search_health')
channel.queue_declare(queue='precedent_search_health_return')
#queue to send and receive messages from statute verification module
channel.queue_declare(queue='statute_verification_health')
channel.queue_declare(queue='statute_verification_health_return')
#queue to send and receive messages from summarization module
channel.queue_declare(queue='summarization_health')
channel.queue_declare(queue='summarization_health_return')

contract = False
ocr = False
precedent_search = False
statute_verification = False
summarization = False


def contract_health():
    global contract
    message = 'RabbitMQ connection established successfully to contract module'
    # Publish message to contract_health queue
    channel.basic_publish(exchange='', routing_key='contract_health', body=message)

    # Synchronously get the response from the contract_health_return queue
    method_frame, header_frame, body = channel.basic_get(queue='contract_health_return', auto_ack=True)
    if method_frame:
        body = body.decode()
        data = json.loads(body)
        if data == '200 OK':
            contract = True

def ocr_health():
    global ocr
    message = 'RabbitMQ connection established successfully to ocr module'
    # Publish message to contract_health queue
    channel.basic_publish(exchange='', routing_key='ocr_health', body=message)

    # Synchronously get the response from the contract_health_return queue
    method_frame, header_frame, body = channel.basic_get(queue='ocr_health_return', auto_ack=True)
    if method_frame:
        body = body.decode()
        data = json.loads(body)
        if data == '200 OK':
            ocr = True

def precedent_health():
    global precedent_search
    message = 'RabbitMQ connection established successfully to precedent module'
    # Publish message to contract_health queue
    channel.basic_publish(exchange='', routing_key='precedent_search_health', body=message)

    # Synchronously get the response from the contract_health_return queue
    method_frame, header_frame, body = channel.basic_get(queue='precedent_search_health_return', auto_ack=True)
    if method_frame:
        body = body.decode()
        data = json.loads(body)
        if data == '200 OK':
            precedent_search = True

def summarization_health():
    global summarization
    message = 'RabbitMQ connection established successfully to summarization module'
    # Publish message to contract_health queue
    channel.basic_publish(exchange='', routing_key='summarization_health', body=message)

    # Synchronously get the response from the contract_health_return queue
    method_frame, header_frame, body = channel.basic_get(queue='summarization_health_return', auto_ack=True)
    if method_frame:
        body = body.decode()
        data = json.loads(body)
        if data == '200 OK':
            summarization = True

def statute_health():
    global statute_verification
    message = 'RabbitMQ connection established successfully to statute verification module'
    # Publish message to contract_health queue
    channel.basic_publish(exchange='', routing_key='statute_verification_health', body=message)

    # Synchronously get the response from the contract_health_return queue
    method_frame, header_frame, body = channel.basic_get(queue='statute_verification_health_return', auto_ack=True)
    if method_frame:
        body = body.decode()
        data = json.loads(body)
        if data == '200 OK':
            statute_verification = True

def callback(ch, method, properties, body):
    print(" [x] Received %r" % body)
    print(" [x] Done")
    #set all the health check variables to false
    global contract, ocr, precedent_search, summarization, statute_verification
    contract = False
    ocr = False
    precedent_search = False
    summarization = False
    statute_verification = False

    # ch.basic_ack(delivery_tag = method.delivery_tag)
    #call all the health check functions
    contract_health()
    ocr_health()
    precedent_health()
    summarization_health()
    statute_health()
    #TODO: Add other modules health checks and if statement to validate
    #if all modules are healthy message = '200 OK' else message = services that are health and which are not healthy
    message = ''
    if contract and ocr and precedent_search and summarization and statute_verification:
        message = 'RabitMQ Service is working perfectly - 200 OK'
    else:
        message = 'Some services are down find the list below - \n OCR: ' + str(ocr) + '\n Contract: ' + str(contract) + '\n Precedent Search: ' + str(precedent_search) + '\n Summarization: ' + str(summarization) + '\n Statute Verification: ' + str(statute_verification)


    resp = json.dumps(message,default='str')
    channel.basic_publish(exchange='', routing_key='health_check_return', body=resp)


def main():
    channel.basic_consume(queue='health_check', on_message_callback=callback, auto_ack=True)

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
