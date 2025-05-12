import logging
import pymongo
from pymongo import MongoClient
from itemadapter import ItemAdapter


class MongoDBPipeline:
    """Pipeline to store scraped items in MongoDB"""

    collection_name = 'articles'

    def __init__(self, mongo_uri, mongo_db):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.client = None
        self.db = None

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get(
                'MONGODB_URI', 'mongodb://localhost:27017'),
            mongo_db=crawler.settings.get('MONGODB_DATABASE', 'biaslens')
        )

    def open_spider(self, spider):
        """Connect to MongoDB when spider opens"""
        try:
            self.client = MongoClient(self.mongo_uri)
            self.db = self.client[self.mongo_db]
            logging.info(
                f"Connected to MongoDB: {self.mongo_uri}, database: {self.mongo_db}")
        except Exception as e:
            logging.error(f"Failed to connect to MongoDB: {str(e)}")
            raise

    def close_spider(self, spider):
        """Close MongoDB connection when spider closes"""
        if self.client:
            self.client.close()
            logging.info("MongoDB connection closed")

    def process_item(self, item, spider):
        """Process each item and save to MongoDB"""
        adapter = ItemAdapter(item)

        # Clean the content if it contains HTML
        content = adapter.get('content')
        if content and ('<' in content or '>' in content):
            # Simple HTML stripping
            import re
            content = re.sub('<[^<]+?>', '', content)
            adapter['content'] = content.strip()

        # Use URL as unique key
        url = adapter.get('url')
        if not url:
            logging.warning("Item has no URL, skipping MongoDB storage")
            return item

        # Store to MongoDB using upsert
        try:
            self.db[self.collection_name].update_one(
                {'url': url},
                {'$set': dict(adapter)},
                upsert=True
            )
            logging.debug(f"Saved article to MongoDB: {url}")
        except Exception as e:
            logging.error(f"Error saving to MongoDB: {str(e)}")

        return item
