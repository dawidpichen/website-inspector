import configparser


def read_configs_from_ini(file, section):
    # Function return a dictionary containing all the values from a specified section in INI file.
    configs = {}
    parser = configparser.ConfigParser()
    parser.read(file)
    for key in parser[section]:
        configs[key] = parser[section][key]
    return configs


def read_sites_configuration_file(file):
    # Function returns a list of tuples containing site configurations, a tuple has two members (url, regex),
    # however the second gets set to None if it is not provided.
    configs = []
    with open(file, 'r', encoding="utf-8") as f:
        for line in f:
            if line.isspace():
                continue  # Blank line, go to next line.
            line = line.rstrip()  # Remove new-line and other whitespace characters from line
            # TODO Should be improved in tne future, as it might me desired the have trailing white spaces in regex.
            partitioned_values = line.partition(" ")
            if partitioned_values[1] == "":
                # There is no space in the configuration, therefore we are just dealing with URL only.
                configs.append((partitioned_values[0], None))
            else:
                # Configuration also contains the regular expression.
                configs.append((partitioned_values[0], partitioned_values[2]))
    return configs


