import logging
import time
from flask import Flask, request, render_template, g
import pika
import json
import queue  # Import the queue module

app = Flask(
    __name__,
    template_folder='templates'
)


# RabbitMQ connection setup
connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

channel.queue_declare(queue='health_check')
channel.queue_declare(queue='health_check_return')
channel.queue_declare(queue='summary')
channel.queue_declare(queue='summary_return')


channel.queue_declare(queue='item_creation')
channel.queue_declare(queue='order_processing')
channel.queue_declare(queue='return_order_processing')
channel.queue_declare(queue='stock_management')


@app.route('/')
def index():
    return render_template('login.html')

@app.route('/admin')
def admin():
    return render_template('index.html')

@app.route('/users')
def user():
    return render_template('user.html')
# Health check endpoint
@app.route('/health_check', methods=['GET'])
def health():
    return render_template('health.html', message='Record Inserted Successfully!')

@app.route('/health_check_actually', methods=['GET'])
def health_check():
    message = 'RabbitMQ connection established successfully'
    # Publish message to health_check queue
    def callback(ch, method, properties, body):
        body = body.decode()
        data = json.loads(body)
        g.healthres = json.dumps(data, default=str)
        channel.stop_consuming()

    channel.basic_publish(exchange='', routing_key='health_check', body=message)
    channel.basic_consume(queue='health_check_return', on_message_callback=callback, auto_ack=True)
    channel.start_consuming()

    return g.get('healthres', 'RabitMQ Service Not working')



# Generate summary endpoint
@app.route('/summary', methods=['POST'])
def insert_record_actually():
    inp_data = request.form['inputData']
    # id = request.form['id']
    # quantity = request.form['quantity']
    # amount = request.form['amount']
    message = json.dumps({'inputData': inp_data})
    logging.info(message)
    # Publish message to insert_record queue
    channel.basic_publish(exchange='', routing_key='summary', body=message)

    def callback(ch, method, properties, body):
        body = body.decode()
        data = json.loads(body)
        g.summaryres = json.dumps(data, default=str)
        channel.stop_consuming()

    channel.basic_consume(queue='summary_return', on_message_callback=callback, auto_ack=True)
    channel.start_consuming()
    return g.get('summaryres', 'No data received')

#
@app.route('/delete_record_actually', methods=['POST'])
def delete_record_actually():
    id = request.form['id']
    quantity = request.form['quantity']
    message = json.dumps({'id': id, 'quantity':quantity})
    logging.info(message)
    # Publish message to delete_record queue
    channel.basic_publish(exchange='', routing_key='stock_management', body=message)
    return render_template('delete.html', message='Record Deleted Successfully!')

# Read database endpoint
@app.route('/read_database', methods=['GET'])
def read_database():
    # Publish message to read_database queue
    return render_template('read.html', message='Read Database message sent!')

@app.route('/read_database_actually', methods=['GET'])
def read_database_actually():
    def callback(ch, method, properties, body):
        body = body.decode()
        data = json.loads(body)
        g.newdata = json.dumps(data, default=str)
        channel.stop_consuming()

    channel.basic_publish(exchange='', routing_key='order_processing', body='')
    channel.basic_consume(queue='return_order_processing', on_message_callback=callback, auto_ack=True)
    channel.start_consuming()

    return g.get('newdata', 'No data received')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)