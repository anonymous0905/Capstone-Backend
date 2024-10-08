# #!/usr/bin/env python
# import pika, sys, os
# import json
# import logging
# import pymongo
#
# # Connect to MongoDB database
# client = pymongo.MongoClient("mongodb://mongodb:27017/")
# db = client["CCRabitMQ"]
# collection = db["Item"]
#
# def main():
#     connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
#     channel = connection.channel()
#
#     channel.queue_declare(queue='item_creation')
#     print("In main")
#     def callback(ch, method, properties, body):
#         # Parse incoming message
#         body = body.decode()
#         body = json.loads(body)
#         # message = json.loads(body)
#         record = {
#             "id": body['id'],
#             "name": body['name'],
#             "quantity": body['quantity'],
#             "amount":body['amount'],
#         }
#         collection.insert_one(record)
#
#         # Acknowledge the message
#         #ch.basic_ack(delivery_tag=method.delivery_tag)
#
#     channel.basic_consume(queue='item_creation', on_message_callback=callback, auto_ack=True)
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
#             sys._exit(0)