from db.collection_manager import CollectionManager
from clustering.clustering_service import ClusteringService
import logging
import os
import sys
import importlib
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from biaslens.biaslens.spiders import BBCSpider
from biaslens.fact_extraction import cluster_fact_extraction

# Add the project root to the Python path
root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_path)

# Add the Scrapy project path
scrapy_path = os.path.join(root_path, 'biaslens')
sys.path.append(scrapy_path)

# Import the Spider directly
# Import our clustering service using absolute path


class ETLPipelineRunner:
    """Class to run the ETL pipeline for BiasLens"""

    def __init__(self):
        self.clustering_service = ClusteringService()

        # Set up Scrapy settings with correct paths
        self.settings = get_project_settings()
        # Add settings for MongoDB if not already in settings.py
        self.settings.set('MONGODB_URI', 'mongodb://localhost:27017')
        self.settings.set('MONGODB_DATABASE', 'biaslens')

        # Make sure Scrapy can find your spiders
        if 'SPIDER_MODULES' not in self.settings:
            print("Setting SPIDER_MODULES manually...")
            self.settings.set('SPIDER_MODULES', [
                              'biaslens.biaslens.spiders', 'biaslens.spiders'])

    def run_spider(self, spider_class=BBCSpider.BbcspiderSpider):
        """Run the Scrapy spider to collect articles"""
        logging.info(f"Starting spider: {spider_class.name}")

        # Pass the spider class directly rather than the name
        process = CrawlerProcess(self.settings)
        process.crawl(spider_class)
        process.start()  # This will block until crawling is finished

        logging.info(f"Spider {spider_class.name} completed")

    def run_clustering(self):
        """Run clustering on all articles"""
        collection_manager = CollectionManager()
        all_articles = collection_manager.get_all_articles()

        logging.info(f"Running clustering on {len(all_articles)} articles")

        # clear previous cluster collections
        self.clustering_service.clear_cluster_collections()

        # Process articles for clustering
        cluster_stats = self.clustering_service.process_new_articles(
            all_articles)

        # create visualization of clusters
        # self.clustering_service.create_visualizations(cluster_stats)

        logging.info(
            f"Clustering complete. Found {len(cluster_stats)} clusters")
        return cluster_stats

    def run_fact_extraction(self):
        """Run fact extraction on clustered articles"""
        logging.info("Running fact extraction on clustered articles")
        collection_manager = CollectionManager()

        # Get all cluster IDs from the clusters collection
        clusters = list(collection_manager.clusters_collection.find(
            {}, {"cluster_id": 1}))

        if not clusters:
            logging.warning("No clusters found for fact extraction")
            return

        logging.info(f"Found {len(clusters)} clusters for fact extraction")

        # Process each cluster
        for cluster_data in clusters:
            cluster_id = cluster_data.get("cluster_id")
            if cluster_id is None:
                continue

            logging.info(f"Processing facts for cluster {cluster_id}")

            # Get articles from this cluster
            try:
                cluster_articles = collection_manager.get_all_headlines_and_articles_from_cluster(
                    str(cluster_id))
                logging.info(
                    f"Found {len(cluster_articles)} articles in cluster {cluster_id}")

                # Prepare articles in the format needed for fact extraction
                articles_for_extraction = []
                for article in cluster_articles:
                    # The 'article' field in your function might be causing confusion
                    # Let's ensure we have the content field available
                    if "content" not in article and "article" in article:
                        article["content"] = article["article"]

                    # Add required fields for fact extraction
                    article["id"] = article.get("_id")
                    article["cluster_id"] = cluster_id
                    article["source"] = article.get("source", "unknown")

                    articles_for_extraction.append(article)

                # Extract and store facts
                if articles_for_extraction:
                    logging.info(
                        f"Extracting facts from {len(articles_for_extraction)} articles in cluster {cluster_id}")
                    cluster_fact_extraction.get_cluster_facts_and_store_in_mongo(
                        articles_for_extraction)

                    # cluster_fact_extraction.visualize_article_and_fact_word_counts(
                    # articles_for_extraction)

                else:
                    logging.warning(
                        f"No valid articles found for fact extraction in cluster {cluster_id}")

            except Exception as e:
                logging.error(
                    f"Error processing facts for cluster {cluster_id}: {str(e)}")

        logging.info("Fact extraction completed")

    def run_full_pipeline(self):
        """Run the full ETL pipeline"""
        logging.info("Starting full ETL pipeline")

        # Step 1: Run the spider - pass the class directly
        self.run_spider()

        # Step 2: Run clustering
        self.run_clustering()

        # Step 3: Run fact extraction
        self.run_fact_extraction()

        logging.info("ETL pipeline completed successfully")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Print useful diagnostic information
    print(f"Python path: {sys.path}")
    print(f"Current directory: {os.getcwd()}")

    # Run the pipeline
    runner = ETLPipelineRunner()
    runner.run_full_pipeline()
