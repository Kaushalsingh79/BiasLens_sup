from pymongo import MongoClient
import logging


class MongoDBClient:
    """Singleton class for MongoDB connection"""
    _instance = None

    def __new__(cls, uri=None, db_name=None):
        if cls._instance is None:
            cls._instance = super(MongoDBClient, cls).__new__(cls)
            cls._instance.client = None
            cls._instance.db = None
            cls._instance.initialize(uri, db_name)
        return cls._instance

    def initialize(self, uri=None, db_name=None):
        """Initialize connection with MongoDB"""
        if not uri:
            uri = "mongodb://localhost:27017"
        if not db_name:
            db_name = "biaslens"

        try:
            self.client = MongoClient(uri)
            self.db = self.client[db_name]
            logging.info(f"Connected to MongoDB database: {db_name}")
        except Exception as e:
            logging.error(f"Failed to connect to MongoDB: {str(e)}")
            raise

    def get_collection(self, collection_name):
        """Get a MongoDB collection by name"""
        if self.db is None:
            raise Exception("MongoDB database not initialized")
        return self.db[collection_name]

    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logging.info("MongoDB connection closed")
