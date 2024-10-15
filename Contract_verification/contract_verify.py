
#!/usr/bin/env python
import pika, sys, os
import json
connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

channel.queue_declare(queue='contract_health')
channel.queue_declare(queue='contract_health_return')
channel.queue_declare(queue='contract')
channel.queue_declare(queue='contract_return')

def callback(ch, method, properties, body):
    print(" [x] Received %r" % body)
    print(" [x] Done")
    # ch.basic_ack(delivery_tag = method.delivery_tag)
    message = '200 OK'
    resp = json.dumps(message,default='str')
    channel.basic_publish(exchange='', routing_key='contract_health_return', body=resp)


def callback_contract(ch, method, properties, body):
    print(" [x] Received %r" % body)
    print(" [x] Done")
    # ch.basic_ack(delivery_tag = method.delivery_tag)
    #extract the message from the body
    message = json.loads(body)
    print(message)
    text = message['inputData']
    print(text)
    #TODO: Implement contract verification logic here
    message = '200 OK - Contract verified successfully'
    resp = json.dumps(message,default='str')
    channel.basic_publish(exchange='', routing_key='contract_return', body=resp)

def main():
    channel.basic_consume(queue='contract_health', on_message_callback=callback, auto_ack=True)
    channel.basic_consume(queue='contract', on_message_callback=callback_contract, auto_ack=True)

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
