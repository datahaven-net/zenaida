#!/usr/bin/env python

import sys
import logging
import json
import pika

#------------------------------------------------------------------------------

logger = logging.getLogger(__name__)

#------------------------------------------------------------------------------

from zepp import epp_client

from lib import xml2json

#------------------------------------------------------------------------------

class XML2JsonOptions(object):
    pretty = True


class GateServer(object):

    def __init__(self, epp_params, connection_params, queue_name):
        self.epp_connection = None
        self.connection = None
        self.epp_params = epp_params
        self.conn_params = connection_params
        self.queue_name = queue_name

    def run(self):
        logger.info('starting new EPP connection at %r:%r', self.epp_params[0], self.epp_params[1])
        logger.info('epp login ID: %r', self.epp_params[2])
        self.epp_connection = epp_client.EPPConnection(
            host=self.epp_params[0],
            port=int(self.epp_params[1]),
            user=self.epp_params[2],
            password=self.epp_params[3],
        )
        logger.info('starting new connection with the queue service at %r:%r', self.conn_params[0], self.conn_params[1])
        logger.info('queue service user ID: %r', self.conn_params[2])
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=self.conn_params[0],
                port=int(self.conn_params[1]),
                virtual_host='/',
                credentials=pika.PlainCredentials(self.conn_params[2], self.conn_params[3]),
            ))
        self.channel = self.connection.channel()
        logger.info('queue name is: %r', self.queue_name)
        result = self.channel.queue_declare(queue=self.queue_name)  # , exclusive=True)
        self.channel.basic_qos(prefetch_count=1)
        self.callback_queue = result.method.queue
        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_request,
            # auto_ack=True,
        )
        logger.info('awaiting RPC requests')
        self.channel.start_consuming()

    def on_request(self, inp_channel, inp_method, inp_props, request):
        try:
            request_json = json.loads(request)
        except Exception as exc:
            logger.error('Failed processing %r : %r', request, exc)
            response_error = {'error': str(exc), }
            response_raw = json.dumps(response_error)
            return self.do_send_reply(inp_channel, inp_props, inp_method, response_raw)
        response_json = self.do_process_epp_command(request_json)
        response_raw = json.dumps(response_json)
        return self.do_send_reply(inp_channel, inp_props, inp_method, response_raw)

    def do_send_reply(self, inp_channel, inp_props, inp_method, response_raw):
        inp_channel.basic_publish(
            exchange='',
            routing_key=inp_props.reply_to,
            properties=pika.BasicProperties(correlation_id=inp_props.correlation_id),
            body=response_raw,
        )
        inp_channel.basic_ack(delivery_tag=inp_method.delivery_tag)
        return True

    def do_process_epp_command(self, request_json):
        cmd = request_json['cmd']
        args = request_json.get('args', {})
        response_xml = ''
        if cmd == 'poll_req':
            response_xml = self.epp_connection.poll(raw_response=True)
        try:
            response_json = json.loads(xml2json.xml2json(response_xml, XML2JsonOptions(), strip_ns=1, strip=1))
        except UnicodeEncodeError:
            response_json = json.loads(xml2json.xml2json(response_xml.encode('ascii', errors='ignore'), XML2JsonOptions(), strip_ns=1, strip=1))
        print('response_json', response_json)
        return response_json

#------------------------------------------------------------------------------

def main():
    logging.basicConfig(
        level=logging.DEBUG,
        stream=sys.stdout,
        format='%(asctime)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    logging.getLogger('pika').setLevel(logging.INFO)

    GateServer(
        epp_params=open(sys.argv[1], 'r').read().split(' '),
        connection_params=open(sys.argv[2], 'r').read().split(' '),
        queue_name='epp_messages',
    ).run()
    return True


if __name__ == "__main__":
    sys.exit(int(not main()))
