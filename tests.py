import unittest
from libs import config_reader
import monitor


class TestConfigFile(unittest.TestCase):
    def test_not_existing_setting(self):
        config = config_reader.read_configs_from_ini('configs/general.ini', 'Monitoring')
        with self.assertRaises(KeyError):
            v = config['frequencyXXXX']

    def test_frequency_setting(self):
        config = config_reader.read_configs_from_ini('configs/general.ini', 'Monitoring')
        self.assertGreater(int(config['frequency']), 0, 'Invalid frequency value.')

    def test_site_existence_in_configuration(self):
        monitored_sites = config_reader.read_sites_configuration_file('configs/monitored-sites.conf')
        self.assertIn(('http://olesno.pl/', None), monitored_sites)


class TestMonitor(unittest.TestCase):
    def test_existing_site(self):
        checker = monitor.WebsiteChecker('http://olesno.pl')
        result = checker.check()
        self.assertEqual(result['code'], 200)

    def test_existing_site_and_regex(self):
        checker = monitor.WebsiteChecker('http://olesno.pl',
                                         'nr konta: [\\d]{2} [\\d]{4} [\\d]{4} [\\d]{4} [\\d]{4} [\\d]{4} [\\d]{4}')
        result = checker.check()
        self.assertEqual(result['code'], 200)

    def test_existing_site_and_not_matched_regex(self):
        checker = monitor.WebsiteChecker('http://olesno.pl', 'Dawid Pichen')
        result = checker.check()
        self.assertEqual(result['code'], monitor.WebsiteChecker.DID_NOT_FIND_PATTERN)

    def test_not_existing_site(self):
        checker = monitor.WebsiteChecker('http://pichen-xxx.com')
        result = checker.check()
        self.assertEqual(result['code'], monitor.WebsiteChecker.COULD_NOT_CONNECT)


if __name__ == '__main__':
    unittest.main()
