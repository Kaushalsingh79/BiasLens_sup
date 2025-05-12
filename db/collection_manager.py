from db.mongo_client import MongoDBClient
import logging


class CollectionManager:
    """Manager for MongoDB collections related to article clusters"""

    def __init__(self):
        self.mongo_client = MongoDBClient()
        # Collection to store all articles
        self.articles_collection = self.mongo_client.get_collection("articles")
        # Collection to store cluster metadata
        self.clusters_collection = self.mongo_client.get_collection("clusters")

    def create_cluster_collection(self, cluster_id):
        """Create or get collection for a specific cluster"""
        collection_name = f"cluster_{cluster_id}"
        return self.mongo_client.get_collection(collection_name)

    def save_article(self, article_data):
        """Save an article to the main articles collection"""
        # Use URL as unique identifier
        url = article_data.get("url")
        if not url:
            logging.warning("Article has no URL, cannot save to MongoDB")
            return None

        # Use upsert to update if exists or insert if doesn't
        result = self.articles_collection.update_one(
            {"url": url},
            {"$set": article_data},
            upsert=True
        )
        return result

    def save_article_to_cluster(self, article_data, cluster_id):
        """Save an article to its cluster collection"""
        cluster_collection = self.create_cluster_collection(cluster_id)
        url = article_data.get("url")

        if not url:
            logging.warning(
                f"Article has no URL, cannot save to cluster {cluster_id}")
            return None

        # Update article with cluster ID
        article_data["cluster_id"] = cluster_id

        # Use upsert to update if exists or insert if doesn't
        result = cluster_collection.update_one(
            {"url": url},
            {"$set": article_data},
            upsert=True
        )

        # Also update cluster info in main collection
        self.articles_collection.update_one(
            {"url": url},
            {"$set": {"cluster_id": cluster_id}}
        )

        return result

    def update_cluster_metadata(self, cluster_id, metadata):
        """Update metadata for a cluster"""
        return self.clusters_collection.update_one(
            {"cluster_id": cluster_id},
            {"$set": metadata},
            upsert=True
        )

    def get_all_articles(self):
        """Get all articles from the main collection"""
        return list(self.articles_collection.find())

    def get_all_headlines_and_articles_from_cluster(self, cluster_id: str) -> list:
        """Get all headlines and articles from a specific cluster"""
        count = self.articles_collection.count_documents({})
        logging.info(f"Found {count} articles in collection")
        cluster_collection = self.create_cluster_collection(cluster_id)
        return list(cluster_collection.find({}, {"headline": 1, "content": 1, "source": 1}))
