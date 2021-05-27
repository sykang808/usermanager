from kafka import KafkaConsumer 
from kafka import KafkaProducer 
from json import loads 
from json import dumps 
import requests
import threading
import json
import logging
logging.basicConfig(filename='debug.log',level=logging.DEBUG)
import boto3
from botocore.config import Config

my_config = Config(
    region_name='us-west-2',
)
#t = get_secret()
#print(DATABASE_CONFIG)
cloudformation_client = boto3.client('cloudformation', config=my_config)
response = cloudformation_client.describe_stacks(
    StackName='MicroserviceCDKVPC'
)
ParameterKey=''
outputs = response["Stacks"][0]["Outputs"]
for output in outputs:
    keyName = output["OutputKey"]
    if keyName == "mskbootstriapbrokers":
        ParameterKey = output["OutputValue"]

print( ParameterKey )
ssm_client = boto3.client('ssm', config=my_config)
response = ssm_client.get_parameter(
    Name=ParameterKey
)
BOOTSTRAP_SERVERS = response['Parameter']['Value'].split(',')

 
class UserManager():
    producer = KafkaProducer(acks=0, compression_type='gzip',bootstrap_servers=BOOTSTRAP_SERVERS, security_protocol="SSL", value_serializer=lambda v: json.dumps(v, sort_keys=True).encode('utf-8'))    
    ret_fin = 0
    ret_message = ''

    def register_kafka_listener(self, topic):
        # Poll kafka
        def poll():
            # Initialize consumer Instance
            consumer = KafkaConsumer(topic,security_protocol="SSL", bootstrap_servers=BOOTSTRAP_SERVERS, auto_offset_reset='earliest', enable_auto_commit=True, 
                                        group_id='my-mc' )

            print("About to start polling for topic:", topic)
            consumer.poll(timeout_ms=6000)
            print("Started Polling for topic:", topic)
            for msg in consumer:
                self.kafka_listener(msg)
        print("About to register listener to topic:", topic)
        t1 = threading.Thread(target=poll)
        t1.start()
        print("started a background thread")

    def on_send_success(self, record_metadata):
        logging.debug("topic: %s" % record_metadata.topic)
        self.ret_fin = 200
        self.ret_message = "successkafkacheckuser"

    def on_send_error(self, excp):
        print("error : %s" % excp)
        self.producer.flush() 
        self.ret_fin = 400
        self.ret_message = "failkafkacheckuser"

    def sendkafka(self, topic,data, status):
        data['status'] = status
        self.producer.send( topic, value=data).get()#add_callback(self.on_send_success).add_errback(self.on_send_error) 
        self.producer.flush() 


    def kafka_listener(self, data):
    #   print("ordermanager:", data.value.decode("utf-8"))
        json_data = json.loads(data.value.decode("utf-8"))
        url= 'http://flask-restapi.user/user/' + str(json_data['customer_id'])       
        r = requests.get( url )
        
        if r.status_code != 200:
            self.sendkafka("orderkafka", json_data, "fail-kafka-user")
            return;  

        ret_json = json.loads(r.content)
        if ret_json['money'] - ( json_data['count'] * json_data['price']) < 0 :
            self.sendkafka("orderkafka", json_data, "fail-lack-kafka-user") 
            return;

        ret_json['money'] -= (json_data['count'] * json_data['price'])
        ret_json = json.dumps(ret_json)
        r = requests.patch( url ,ret_json)          
        if r.status_code != 200:
            self.sendkafka("orderkafka", json_data, "fail-reduce-kafka-user")
            return;  

        self.sendkafka("orderkafka", json_data, "success-kafka-user")                
            
        logging.debug( {'message': json_data } )


         
if __name__ == '__main__':
#    OrderManager.register_kafka_listener('orderkafka')
#   app.run(host="0.0.0.0", port=5052,debug=True)
    usermanager1 = UserManager()
    usermanager1.register_kafka_listener('userkafka')
    usermanager2 = UserManager()
    usermanager2.register_kafka_listener('userkafka')
    usermanager3 = UserManager()
    usermanager3.register_kafka_listener('userkafka')
    usermanager4 = UserManager()
    usermanager4.register_kafka_listener('userkafka')