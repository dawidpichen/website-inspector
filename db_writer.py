import json
from kafka import KafkaConsumer
from kafka import errors
from libs import config_reader
from datetime import datetime, timezone
import psycopg2

scriptTitle = "Monitoring Results Database Writer"
scriptVersion = "1.0"
scriptCopyright = "(C) 2020 Dawid Pichen."


class DatabaseWriter:
    def __init__(self, kafka_config, pgsql_config):
        try:
            # Let's connect to Kafka broker and set up the way to decode the received messages (JSON encoded in UTF-8).
            self._consumer = KafkaConsumer(kafka_config['topic'], bootstrap_servers=kafka_config['server'],
                                           security_protocol=kafka_config['protocol'],
                                           ssl_cafile=kafka_config['ssl-ca-file'],
                                           ssl_certfile=kafka_config['ssl-cert-file'],
                                           ssl_keyfile=kafka_config['ssl-key-file'],
                                           auto_offset_reset='earliest', enable_auto_commit=True,
                                           group_id='dpp-group',
                                           value_deserializer=lambda obj: json.loads(obj.decode('utf-8')))
        except errors.NoBrokersAvailable:
            raise Exception("Could not connect to Kafka!")
        self._db = psycopg2.connect(host=pgsql_config['server'], port=pgsql_config['port'], user=pgsql_config['login'],
                                    password=pgsql_config['password'], database=pgsql_config['db'])
        self._cursor = self._db.cursor()
        print("Connected to DB.")

    def close_db_connection(self):
        if self._cursor:
            self._cursor.close()
        if self._db:
            self._db.close()
        print("Closed connection to DB.")

    def move_messages_to_db(self):
        for messageObject in self._consumer:
            message = messageObject.value
            check_up_time = datetime.fromtimestamp(message['date'], timezone.utc)  # Convert time back to datetime
            # format talking into consideration that the received value is in UTC time zone.
            regexp = message['regexp'] if message['regexp'] else ''  # Converting regexp to string in case it is empty.
            url = message['url']
            # Look up for siteid for received URL and regexp.
            self._cursor.execute("SELECT siteid FROM sites WHERE url = %s AND regexp = %s", (url, regexp))
            record = self._cursor.fetchone()
            if record:
                # The siteid has been found in DB, we can use it right away.
                site_id = record[0]
            else:
                # We need to add the lookup record to the master table first.
                self._cursor.execute("INSERT INTO sites (url, regexp) VALUES (%s, %s) RETURNING siteid", (url, regexp))
                site_id = self._cursor.fetchone()[0]
            # Add checkup record
            self._cursor.execute("INSERT INTO checks (siteid, checkuptime, code, responsetime) VALUES (%s, %s, %s, %s)",
                                 (site_id, check_up_time, message['code'], message['responseTime']))
            self._db.commit()
            print('Result {0} for site "{1}" dated {2} added to DB.'.format(message['code'], url,
                                                                            check_up_time.astimezone().ctime()))


# The execution of the script starts here.
if __name__ == "__main__":
    print(f'{scriptTitle} (v. {scriptVersion})\n{scriptCopyright}\n')
    # Load all necessary configurations:
    kafkaConfig = config_reader.read_configs_from_ini('configs/general.ini', 'Kafka')
    pgsqlConfig = config_reader.read_configs_from_ini('configs/general.ini', 'PostgreSQL')
    dbWriter = DatabaseWriter(kafkaConfig, pgsqlConfig)
    try:
        dbWriter.move_messages_to_db()
    finally:
        dbWriter.close_db_connection()
