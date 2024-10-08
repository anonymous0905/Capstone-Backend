#
# #!/usr/bin/env python
# import pika, sys, os
# import json
# connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
# channel = connection.channel()
#
# channel.queue_declare(queue='health_check')
# channel.queue_declare(queue='health_check_return')
#
#
# def callback(ch, method, properties, body):
#     print(" [x] Received %r" % body)
#     print(" [x] Done")
#     # ch.basic_ack(delivery_tag = method.delivery_tag)
#     message = 'RabitMQ Service is working perfectly - 200 OK'
#     resp = json.dumps(message,default='str')
#     channel.basic_publish(exchange='', routing_key='health_check_return', body=resp)
#
#
# def main():
#     channel.basic_consume(queue='health_check', on_message_callback=callback, auto_ack=True)
#
#     print(' [*] Waiting for messages. To exit press CTRL+C')
#     channel.start_consuming()
#
# if __name__ == '__main__':
#     try:
#         main()
#     except KeyboardInterrupt:
#         print('Interrupted')
#         try:
#             sys.exit(0)
#         except SystemExit:
#             os._exit(0)
