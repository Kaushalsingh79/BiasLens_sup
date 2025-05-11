from db.collection_manager import CollectionManager
from clustering.article_clustering import ArticleClustering
import logging
import datetime


class ClusteringService:
    """Service to manage article clustering and database storage"""

    def __init__(self):
        self.collection_manager = CollectionManager()
        self.clustering = ArticleClustering()

    def process_new_articles(self, articles):
        """
        Process newly scraped articles

        1. Save articles to main collection
        2. Get all articles for clustering
        3. Perform clustering
        4. Update articles with cluster information
        5. Save articles to their respective cluster collections
        """
        # First save all new articles to main collection
        for article in articles:
            self.collection_manager.save_article(article)

        # Get all articles for clustering
        all_articles = self.collection_manager.get_all_articles()

        # Perform clustering
        logging.info(f"Clustering {len(all_articles)} articles")
        clustered_df = self.clustering.cluster_articles(all_articles)

        # Update cluster collections
        cluster_stats = {}
        for _, row in clustered_df.iterrows():
            article = row['article']
            cluster_id = int(row['cluster'])

            # Skip noise points (cluster = -1) or handle them differently
            if cluster_id == -1:
                cluster_id = -1  # Store unclustered articles in their own collection

            # Add to cluster-specific collection
            self.collection_manager.save_article_to_cluster(
                article, cluster_id)

            # Update cluster stats
            if cluster_id not in cluster_stats:
                cluster_stats[cluster_id] = {
                    "count": 0,
                    "articles": []
                }
            cluster_stats[cluster_id]["count"] += 1
            cluster_stats[cluster_id]["articles"].append({
                "url": article.get("url"),
                "headline": article.get("headline")
            })

        # Update cluster metadata
        for cluster_id, stats in cluster_stats.items():
            metadata = {
                "cluster_id": cluster_id,
                "article_count": stats["count"],
                "articles": stats["articles"],
                "last_updated": datetime.datetime.now()
            }
            self.collection_manager.update_cluster_metadata(
                cluster_id, metadata)

        logging.info(f"Updated {len(cluster_stats)} clusters")
        return cluster_stats
