
#!/usr/bin/env python
import pika, sys, os
import json
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
    # ch.basic_ack(delivery_tag = method.delivery_tag)
    #extract the message from the body
    message = json.loads(body)
    print(message)
    text = message['inputData']
    print(text)
    #TODO: Implement statute verification logic here
    message = '200 OK - Statute verified successfully'
    resp = json.dumps(message,default='str')
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
