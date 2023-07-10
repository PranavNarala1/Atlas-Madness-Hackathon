from pymongo import MongoClient

import certifi


def get_database():
    CONNECTION_STRING = "mongodb+srv://hackathon:Atlas734&@cluster0.vkwblp2.mongodb.net/"


    # Create a connection using MongoClient. You can import MongoClient or use pymongo.MongoClient
    client = MongoClient(CONNECTION_STRING, tlsCAFile=certifi.where())
    # Create the database for our example (we will use the same database throughout the tutorial
    return client['mongoDB_atlas']
  
# This is added so that many files can reuse the function get_database()
if __name__ == "__main__":
    dbname = get_database()