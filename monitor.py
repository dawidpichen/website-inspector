import re
import urllib.request
import urllib.error
import time
from kafka import KafkaProducer
from kafka import errors
from libs import config_reader
import json

scriptTitle = "Website Monitor"
scriptVersion = "1.0"
scriptCopyright = "(C) 2020 Dawid Pichen."


class WebsiteChecker:  # Class responsible for checking the websites.
    COULD_NOT_CONNECT = 700  # Used to indicate that there was a general connection problem (e.g. DNS record doesn't
    # exists, server rejected the connection etc.).
    DID_NOT_FIND_PATTERN = 701  # Used to indicate that the server returned the content (200) but there was no
    # match with provided regular expression.

    def __init__(self, url, expected_regex = None):  # Initialise the class object with values.
        self._url = url
        self._regex = expected_regex
        self._regexCompiled = re.compile(expected_regex) if expected_regex else None  # Regular expression is being
        # compiled upon class creation for performance.

    def check(self):
        # Function returns result of a check as a dictionary with values stored in self-explanatory keys.
        page_content = None
        check_time = time.time()  # Gets the current precise time
        try:
            connection = urllib.request.urlopen(self._url)  # Open the provided URL.
            response_code = connection.getcode()
            if response_code == 200 and self._regexCompiled:  # If server responded OK and there is a regular expression
                # specified, let's download the page.
                page_content = connection.read().decode()
        except urllib.error.HTTPError as error:
            response_code = error.code  # Handles peculiar responses such as "authorisation required".
        except urllib.error.URLError:
            response_code = self.COULD_NOT_CONNECT
        response_time = time.time() - check_time  # Calculates the response time calculating the time difference.
        if page_content and not self._regexCompiled.search(page_content):
            response_code = self.DID_NOT_FIND_PATTERN
        return {'url': self._url, 'regexp': self._regex, 'code': response_code, 'responseTime': response_time,
                'date': check_time}


# The execution of the script starts here.
if __name__ == "__main__":
    print(f'{scriptTitle} (v. {scriptVersion})\n{scriptCopyright}\n')
    # Load all needed configurations.
    kafka_config = config_reader.read_configs_from_ini('configs/general.ini', 'Kafka')
    monitoring_config = config_reader.read_configs_from_ini('configs/general.ini', 'Monitoring')
    monitored_sites = config_reader.read_sites_configuration_file('configs/monitored-sites.conf')
    monitoring_frequency = int(monitoring_config['frequency'])
    checkers = []  # List of WebsiteChecker object with its own configuration based on parsed configuration file.
    for site_config in monitored_sites:
        checkers.append(WebsiteChecker(site_config[0], site_config[1]))

    try:
        # Let's connect to Kafka broker and set up the format of transmitted messages (JSON encoded in UTF-8).
        producer = KafkaProducer(bootstrap_servers=kafka_config['server'], security_protocol=kafka_config['protocol'],
                                 ssl_cafile=kafka_config['ssl-ca-file'], ssl_certfile=kafka_config['ssl-cert-file'],
                                 ssl_keyfile=kafka_config['ssl-key-file'],
                                 value_serializer=lambda obj: json.dumps(obj).encode("utf-8"))
    except errors.NoBrokersAvailable:
        raise Exception("Could not connect to Kafka!")

    while True:
        # This infinitive loop gets check result for each site and send it to Kafka, when done it waits for amount of
        # time specified as frequency and repeats the this operation over again.
        for checker in checkers:
            result = checker.check()
            producer.send(kafka_config['topic'], value=result)
            print('Monitoring result ({0}) for "{1}" collected at {2} sent to Kafka.'.format(result['code'],
                                                                                             result['url'],
                                                                                             time.ctime(result['date'])))
        producer.flush()  # Makes sure that all the messages are sent to Kafka.
        time.sleep(monitoring_frequency)
