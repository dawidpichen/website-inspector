from libs import config_reader
import psycopg2

scriptTitle = "Database Initialise Script"
scriptVersion = "1.0"
scriptCopyright = "(C) 2020 Dawid Pichen."

print(f'{scriptTitle} (v. {scriptVersion})\n{scriptCopyright}\n')
dbConfig = config_reader.read_configs_from_ini('configs/general.ini', 'PostgreSQL')
dbConnection = psycopg2.connect(host=dbConfig['server'], port=dbConfig['port'], user=dbConfig['login'],
                                password=dbConfig['password'], database=dbConfig['db'])
print("Connected to DB.")
try:
    dbCursor = dbConnection.cursor()
    try:
        # First, make sure to get rid of possible existing DB structure in a proper order.
        print("Purging old structure if exists already...")
        dbCursor.execute("ALTER TABLE checks DROP CONSTRAINT IF EXISTS sites_checks")  # Relationship
        dbCursor.execute("ALTER TABLE checks DROP CONSTRAINT IF EXISTS PK_checks")  # Private key
        dbCursor.execute("ALTER TABLE sites DROP CONSTRAINT IF EXISTS PK_sites")  # Private key
        dbCursor.execute("DROP INDEX IF EXISTS url_regex_idx")  # Index
        dbCursor.execute("DROP TABLE IF EXISTS sites")  # Drop master table
        dbCursor.execute("DROP TABLE IF EXISTS checks")  # Drop child table
        # At this point we are sure that nothing is left behind and we can create the main table (sites) which will
        # automatically generate an ID for each pair of site configuration, i.e. URL and regular expression
        # (the latter can not be NULL but can be an empty string).
        print("Creating new structure...")
        dbCursor.execute("""
                CREATE TABLE sites
                (            
                    siteid SERIAL NOT NULL,
                    url CHARACTER VARYING NOT NULL,
                    regexp CHARACTER VARYING NOT NULL,
                    dateadded TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
                )""")
        # To increase the speed of site ID lookups used by "checks" tables, let's add an index on 2 fields used
        # to find out the right ID.
        dbCursor.execute("CREATE UNIQUE INDEX url_regex_idx ON sites (regexp,url)")
        # Adding a primary key will also automatically add an index on "siteid" field.
        dbCursor.execute("ALTER TABLE sites ADD CONSTRAINT PK_sites PRIMARY KEY (siteid)")
        # Create a child table ("checks") which will store the results of the checkups.
        dbCursor.execute("""
                CREATE TABLE checks
                (            
                    siteid INTEGER NOT NULL,
                    checkid BIGSERIAL NOT NULL,
                    checkuptime TIMESTAMP WITH TIME ZONE NOT NULL,
                    code SMALLINT NOT NULL,
                    responsetime NUMERIC(6,3)
                )""")
        dbCursor.execute("ALTER TABLE checks ADD CONSTRAINT PK_checks PRIMARY KEY (siteid, checkid)")
        # Let's create relationship between the 2 tables (add foreign key to "checks" table and set behaviour when the
        # record from the master table gets deleted or updated (cascade, which automatically does same thing in the
        # child table.
        dbCursor.execute("""
                ALTER TABLE checks ADD CONSTRAINT sites_checks FOREIGN KEY (siteid) REFERENCES sites (siteid) 
                ON DELETE CASCADE ON UPDATE CASCADE
                """)
        dbConnection.commit()
        print("Operation completed.")
    finally:
        dbCursor.close()
finally:
    dbConnection.close()
