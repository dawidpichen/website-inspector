import json
from kafka import KafkaConsumer
from kafka import errors
from libs import config_reader
from datetime import datetime, timezone
import psycopg2


class DatabaseWriter:
    def __init__(self, kafka_config, pgsql_config):
        try:
            # Let's connect to Kafka broker and set up the way to decode the received messages (JSON encoded in UTF-8).
            self._consumer = KafkaConsumer(kafka_config['topic'], bootstrap_servers=kafka_config['server'],
                                           security_protocol=kafka_config['protocol'],
                                           ssl_cafile=kafka_config['ssl-ca-file'],
                                           ssl_certfile=kafka_config['ssl-cert-file'],
                                           ssl_keyfile=kafka_config['ssl-key-file'],
                                           auto_offset_reset="earliest", enable_auto_commit=True,
                                           group_id='dpp-group',
                                           value_deserializer=lambda obj: json.loads(obj.decode('utf-8')))
        except errors.NoBrokersAvailable:
            raise Exception("Could not connect to Kafka!")
        self._db = psycopg2.connect(host=pgsql_config['server'], port=pgsql_config['port'], user=pgsql_config['login'],
                                    password=pgsql_config['password'], database=pgsql_config['db'])
        self._cursor = self._db.cursor()

    def close_db_connection(self):
        if self._cursor:
            self._cursor.close()
        if self._db:
            self._db.close()
        print("Closed connection")

    def initialise_db_structure(self):
        # First, make sure to get rid of possible existing DB structure in a proper order.
        self._cursor.execute("ALTER TABLE checks DROP CONSTRAINT IF EXISTS sites_checks")  # Relationship
        self._cursor.execute("ALTER TABLE checks DROP CONSTRAINT IF EXISTS PK_checks")  # Private key
        self._cursor.execute("ALTER TABLE sites DROP CONSTRAINT IF EXISTS PK_sites")  # Private key
        self._cursor.execute("DROP INDEX IF EXISTS url_regex_idx")  # Index
        self._cursor.execute("DROP TABLE IF EXISTS sites")  # Drop master table
        self._cursor.execute("DROP TABLE IF EXISTS checks")  # Drop child table

        # At this point we are sure that nothing is left behind and we can create the main table (sites) which will
        # automatically generate an ID for each pair of site configuration, i.e. URL and regular expression
        # (the latter can not be NULL but can be an empty string).
        self._cursor.execute("""
        CREATE TABLE sites
        (
            siteid SERIAL NOT NULL,
            url CHARACTER VARYING NOT NULL,
            regexp CHARACTER VARYING NOT NULL,
            dateadded TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
        )""")
        # To increase the speed of site ID lookups used by "checks" tables, let's add an index on 2 fields used
        # to find out the right ID.
        self._cursor.execute("CREATE UNIQUE INDEX url_regex_idx ON sites (regexp,url)")
        # Adding a primary key will also automatically add an index on "siteid" field.
        self._cursor.execute("ALTER TABLE sites ADD CONSTRAINT PK_sites PRIMARY KEY (siteid)")
        # Create a child table ("checks") which will store the results of the checkups.
        self._cursor.execute("""
        CREATE TABLE checks
        (
            siteid INTEGER NOT NULL,
            checkuptime TIMESTAMP WITH TIME ZONE NOT NULL,
            code SMALLINT NOT NULL,
            responsetime NUMERIC(6,3)
        )""")
        self._cursor.execute("ALTER TABLE checks ADD CONSTRAINT PK_checks PRIMARY KEY (siteid, checkuptime)")
        # Let's create relationship between the 2 tables (add foreign key to "checks" table and set behaviour when the
        # record from the master table gets deleted or updated (cascade, which automatically does same thing in the
        # child table.
        self._cursor.execute("""
        ALTER TABLE checks ADD CONSTRAINT sites_checks FOREIGN KEY (siteid) REFERENCES sites (siteid) 
        ON DELETE CASCADE ON UPDATE CASCADE
        """)
        self._db.commit()

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
    # Load all necessary configurations:
    kafkaConfig = config_reader.read_configs_from_ini('configs/general.ini', 'Kafka')
    pgsqlConfig = config_reader.read_configs_from_ini('configs/general.ini', 'PostgreSQL')
    dbWriter = DatabaseWriter(kafkaConfig, pgsqlConfig)
    try:
        dbWriter.initialise_db_structure()
        dbWriter.move_messages_to_db()
    finally:
        dbWriter.close_db_connection()
