# website-inspector

## Synopsis

A project consists of 2 main Python scripts which are used to monitor websites availability. The _monitor.py_ 
periodically checks the state of configured websites (using their URLs, but also has support for a regexp pattern 
should to be found in the page) and sends the testing results to specified Kafka broker.
The _db_writer.py_ receives the results from Kafka and writes them to a PostgreSQL database, as the name suggests.

## Standalone or in Containers?

 The scripts can be run directly on a host's system or through Docker containers. The project contains a script to
 build and start necessary containers.
 
 ## What does Website Inspector actually monitors?
 
 It checks the following:
 - a response time, 
 - an error code returned (HTTP specific result code or 700 value when it could not connect), 
 - whether the regexp pattern is found on the page (if not, the error code 701 will indicate it).
 
 ## What goes to a database?
  
  The monitoring results are saved to a PostgreSQL database. 2 tables are used for that purpose 
  (in one-to-many relationship):
  - _SITES_ (a lookup table containing information about websites checked by the monitor along with a 
   _DATEADDED_ field indicating when was the record added for the first time),
  - _CHECKS_ (stored check results, including metric described earlier and the check-up time).
  
 ## Configuration
 
 You must configure the parameters of Kafka broker and a PostgreSQL server, obviously. 
 For that, just update the contents of _configs/general.ini_ configuration file. When needed, please make sure to 
 update additional security files needed by Kafka.
 I have included the configuration to my servers run in the cloud, configured and launched in seconds thanks 
 to Aiven solutions.
 Second step is to configure monitored websites through _configs/monitored-sites.conf_ file. The provided file
 will cause the monitor to check on "olesno.pl" and "pichen.com" websites (the latter also checks for a regexp
 pattern).
 
 **Important note**: Due its changeable nature, the _configs_ directory is not added directly to Docker image, 
 instead it is shared with the host file system upon containers start. 
 
 ## Initial setup
 
Make sure to have Docker installed and running on your Linux and you have access to it.
It is super easy to set-up the whole thing using Docker containers.

1. Go to directory where you cloned the GIT repository.
2. Run this script first (make sure it has the executable flag set): 
`$ ./create_docker_image_and_test.sh` 
It will build the Docker image and immediately test it using a few test cases.
3. Create required DB structure in the database (**WARNING**: it will wipe out existing
_SITES_ and _CHECKS_ tables along with their records): 
`$ ./init_db.sh`

## Running

Whenever you want to start both the monitor and DB writer just use the following script, 
which will start 2 separate containers:

`$ ./start_containers.sh`

Use `docker ps` to see if the containers are running (there should be 2, ie.: _wi-monitor_ and 
_wi-dbwriter_).

Use `docker logs` to see the message reported by scripts. 
 
