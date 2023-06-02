connection = connect(host=host,
                        port=port,
                        dbname=dbname,
                        user=user,
                        password=password)

cursor = connection.cursor()

query = """
    CREATE TABLE users (
        id SERIAL PRIMARY KEY,
        email VARCHAR(150) NOT NULL UNIQUE,
        password VARCHAR(150) NOT NULL,
        created date DEFAULT CURRENT_TIMESTAMP
    )
"""

cursor.execute(query)

connection.commit()
cursor.close()
connection.close()

query = """
    CREATE TABLE connects (
        id SERIAL PRIMARY KEY,
        email VARCHAR(150) NOT NULL,
        customer_id VARCHAR(150),
        connects INTEGER NOT NULL,
        created date DEFAULT CURRENT_TIMESTAMP
    )
"""

query = """
    CREATE TABLE chats (
        id SERIAL PRIMARY KEY,
        email VARCHAR(150) NOT NULL,
        botName VARCHAR(150) NOT NULL,
        chats JSONB NOT NULL,
        created date DEFAULT CURRENT_TIMESTAMP
    )
"""
