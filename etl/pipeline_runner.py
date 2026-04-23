import sys
import os

from twisted.internet import asyncioreactor
try:
    asyncioreactor.install()
except Exception as e:
    print(f"Reactor already installed or error: {e}")
    
# Adds the parent directory (BiasLens) to the system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.collection_manager import CollectionManager
from clustering.clustering_service import ClusteringService
import logging
# import os
# import sys
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


# class ETLPipelineRunner:
#     """Class to run the ETL pipeline for BiasLens"""

#     def __init__(self):
#         self.clustering_service = ClusteringService()

#         # Set up Scrapy settings with correct paths
#         self.settings = get_project_settings()
#         # Add settings for MongoDB if not already in settings.py
#         self.settings.set('MONGODB_URI', 'mongodb://localhost:27017')
#         self.settings.set('MONGODB_DATABASE', 'biaslens')

#         # Make sure Scrapy can find your spiders
#         if 'SPIDER_MODULES' not in self.settings:
#             print("Setting SPIDER_MODULES manually...")
#             self.settings.set('SPIDER_MODULES', [
#                               'biaslens.biaslens.spiders', 'biaslens.spiders'])

#     def run_spider(self, spider_class=BBCSpider.BbcspiderSpider):
#         """Run the Scrapy spider to collect articles"""
#         logging.info(f"Starting spider: {spider_class.name}")

#         # Pass the spider class directly rather than the name
#         process = CrawlerProcess(self.settings)
#         process.crawl(spider_class)
#         process.start()  # This will block until crawling is finished

#         logging.info(f"Spider {spider_class.name} completed")

#     def run_clustering(self):
#         """Run clustering on all articles"""
#         collection_manager = CollectionManager()
#         all_articles = collection_manager.get_all_articles()

#         logging.info(f"Running clustering on {len(all_articles)} articles")

#         # clear previous cluster collections
#         self.clustering_service.clear_cluster_collections()

#         # Process articles for clustering
#         cluster_stats = self.clustering_service.process_new_articles(
#             all_articles)

#         # create visualization of clusters
#         # self.clustering_service.create_visualizations(cluster_stats)

#         logging.info(
#             f"Clustering complete. Found {len(cluster_stats)} clusters")
#         return cluster_stats

#     def run_fact_extraction(self):
#         """Run fact extraction on clustered articles"""
#         logging.info("Running fact extraction on clustered articles")
#         collection_manager = CollectionManager()

#         # Get all cluster IDs from the clusters collection
#         clusters = list(collection_manager.clusters_collection.find(
#             {}, {"cluster_id": 1}))

#         if not clusters:
#             logging.warning("No clusters found for fact extraction")
#             return

#         logging.info(f"Found {len(clusters)} clusters for fact extraction")

#         # Process each cluster
#         for cluster_data in clusters:
#             cluster_id = cluster_data.get("cluster_id")
#             if cluster_id is None:
#                 continue

#             logging.info(f"Processing facts for cluster {cluster_id}")

#             # Get articles from this cluster
#             try:
#                 cluster_articles = collection_manager.get_all_headlines_and_articles_from_cluster(
#                     str(cluster_id))
#                 logging.info(
#                     f"Found {len(cluster_articles)} articles in cluster {cluster_id}")

#                 # Prepare articles in the format needed for fact extraction
#                 articles_for_extraction = []
#                 for article in cluster_articles:
#                     # The 'article' field in your function might be causing confusion
#                     # Let's ensure we have the content field available
#                     if "content" not in article and "article" in article:
#                         article["content"] = article["article"]

#                     # Add required fields for fact extraction
#                     article["id"] = article.get("_id")
#                     article["cluster_id"] = cluster_id
#                     article["source"] = article.get("source", "unknown")

#                     articles_for_extraction.append(article)

#                 # Extract and store facts
#                 if articles_for_extraction:
#                     logging.info(
#                         f"Extracting facts from {len(articles_for_extraction)} articles in cluster {cluster_id}")
#                     cluster_fact_extraction.get_cluster_facts_and_store_in_mongo(
#                         articles_for_extraction)

#                     # cluster_fact_extraction.visualize_article_and_fact_word_counts(
#                     # articles_for_extraction)

#                 else:
#                     logging.warning(
#                         f"No valid articles found for fact extraction in cluster {cluster_id}")

#             except Exception as e:
#                 logging.error(
#                     f"Error processing facts for cluster {cluster_id}: {str(e)}")

#         logging.info("Fact extraction completed")

#     def run_full_pipeline(self):
#         """Run the full ETL pipeline"""
#         logging.info("Starting full ETL pipeline")

#         # Step 1: Run the spider - pass the class directly
#         self.run_spider()

#         # Step 2: Run clustering
#         self.run_clustering()

#         # Step 3: Run fact extraction
#         self.run_fact_extraction()

#         logging.info("ETL pipeline completed successfully")
class ETLPipelineRunner:
    """Class to run the ETL pipeline for BiasLens"""

    def __init__(self):
        self.clustering_service = ClusteringService()
        
        # Set up Scrapy settings with correct paths
        self.settings = get_project_settings()
        # Add settings for MongoDB if not already in settings.py
        self.settings.set('MONGODB_URI', 'mongodb://localhost:27017')
        self.settings.set('MONGODB_DATABASE', 'biaslens')
        
        # IMPORTANT: Enable item pipeline
        self.settings.set('ITEM_PIPELINES', {
            'biaslens.biaslens.pipelines.MongoDBPipeline': 300,
        })
        
        # Make sure Scrapy can find your spiders
        if 'SPIDER_MODULES' not in self.settings:
            self.settings.set('SPIDER_MODULES', ['biaslens.biaslens.spiders', 'biaslens.spiders'])
        
        # Add spider setting
        self.settings.set('NEWSPIDER_MODULE', 'biaslens.biaslens.spiders')

    def run_spider(self, spider_class=BBCSpider.BbcspiderSpider):
        """Run the Scrapy spider to collect articles using CrawlerRunner"""
        import time
        from twisted.internet import reactor
        from scrapy.crawler import CrawlerRunner
        from scrapy.utils.log import configure_logging
        import threading
        
        logging.info(f"Starting spider: {spider_class.name}")
        
        # Disable reactor logging to avoid clutter
        configure_logging({'LOG_LEVEL': 'INFO'})
        
        # Create runner
        runner = CrawlerRunner(self.settings)
        
        # Variable to track completion
        spider_completed = threading.Event()
        spider_error = None
        
        # Start the spider
        deferred = runner.crawl(spider_class)
        
        def spider_finished(result):
            logging.info(f"Spider {spider_class.name} completed successfully")
            spider_completed.set()
            return result
        
        def spider_error_handler(failure):
            nonlocal spider_error
            spider_error = failure
            logging.error(f"Spider failed: {failure}")
            spider_completed.set()
            return failure
        
        deferred.addCallback(spider_finished)
        deferred.addErrback(spider_error_handler)
        
        # Run the reactor if it's not already running
        if not reactor._started:
            reactor.run(installSignalHandlers=False)
        else:
            # If reactor is already running, we need a different approach
            # Wait for completion
            spider_completed.wait()
        
        # Wait a bit for database writes to complete
        time.sleep(3)
        
        if spider_error:
            raise Exception(f"Spider failed: {spider_error}")
        
        logging.info(f"Spider {spider_class.name} completed and database should be updated")

    def debug_check_articles(self):
        """Debug method to check what's in the database"""
        from db.collection_manager import CollectionManager
        import time
        
        # Wait a bit for MongoDB writes to complete
        time.sleep(2)
        
        cm = CollectionManager()
        
        print("\n=== DATABASE DEBUG INFO ===")
        print(f"Database name: {cm.mongo_client.db.name}")
        
        # List all collections
        collections = cm.mongo_client.db.list_collection_names()
        print(f"Available collections: {collections}")
        
        # Check articles collection
        article_count = cm.articles_collection.count_documents({})
        print(f"Articles collection has {article_count} documents")
        
        if article_count > 0:
            sample = cm.articles_collection.find_one()
            print(f"Sample document keys: {sample.keys() if sample else 'None'}")
            print(f"Sample headline: {sample.get('headline', 'N/A') if sample else 'N/A'}")
        
        print("========================\n")
        
        return article_count

    def run_clustering(self):
        """Run clustering on all articles"""
        from db.collection_manager import CollectionManager
        import time
        
        collection_manager = CollectionManager()
        
        # Get articles directly to ensure we have them
        all_articles = list(collection_manager.articles_collection.find({}))
        
        logging.info(f"Running clustering on {len(all_articles)} articles")
        
        if len(all_articles) == 0:
            logging.warning("No articles found in database! Spider may have failed to save.")
            logging.warning("Check if MongoDB is running and spider is configured correctly.")
            return {}
        
        # Clear previous cluster collections
        self.clustering_service.clear_cluster_collections()
        
        # Process articles for clustering
        cluster_stats = self.clustering_service.process_new_articles(all_articles)
        
        logging.info(f"Clustering complete. Found {len(cluster_stats)} clusters")
        return cluster_stats

    def run_fact_extraction(self):
        """Run fact extraction on clustered articles"""
        logging.info("Running fact extraction on clustered articles")
        from db.collection_manager import CollectionManager
        
        collection_manager = CollectionManager()
        
        # Get all cluster IDs from the clusters collection
        clusters = list(collection_manager.clusters_collection.find({}, {"cluster_id": 1}))
        
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
            
            try:
                # Get articles from this cluster - using the cluster collection directly
                cluster_collection = collection_manager.create_cluster_collection(str(cluster_id))
                cluster_articles = list(cluster_collection.find({}))
                
                logging.info(f"Found {len(cluster_articles)} articles in cluster {cluster_id}")
                
                # Also get articles from main collection for this cluster to ensure we have content
                main_articles = list(collection_manager.articles_collection.find(
                    {"cluster_id": cluster_id}
                ))
                
                # Use whichever has content
                articles_to_process = cluster_articles if cluster_articles else main_articles
                
                if articles_to_process:
                    logging.info(f"Extracting facts from {len(articles_to_process)} articles in cluster {cluster_id}")
                    
                    # Ensure each article has content
                    for article in articles_to_process:
                        if "content" not in article and "article" in article:
                            article["content"] = article["article"]
                        if "content" not in article:
                            article["content"] = article.get("description", "")
                    
                    # Import the fact extraction function
                    from biaslens.fact_extraction import cluster_fact_extraction
                    
                    # Extract and store facts
                    cluster_fact_extraction.get_cluster_facts_and_store_in_mongo(
                        articles_to_process
                    )
                else:
                    logging.warning(f"No valid articles found for fact extraction in cluster {cluster_id}")
                    
            except Exception as e:
                logging.error(f"Error processing facts for cluster {cluster_id}: {str(e)}")
                import traceback
                traceback.print_exc()
        
        logging.info("Fact extraction completed")

    def run_full_pipeline(self):
        """Run the full ETL pipeline"""
        logging.info("Starting full ETL pipeline")
        
        try:
            # Step 1: Run the spider
            self.run_spider()
            
            # Step 2: Debug - check articles are saved
            article_count = self.debug_check_articles()
            
            if article_count == 0:
                logging.error("No articles found after spider run. Stopping pipeline.")
                return
            
            # Step 3: Run clustering
            cluster_stats = self.run_clustering()
            
            if not cluster_stats:
                logging.warning("No clusters created. Skipping fact extraction.")
                return
            
            # Step 4: Run fact extraction
            self.run_fact_extraction()
            
            logging.info("ETL pipeline completed successfully")
            
        except Exception as e:
            logging.error(f"Pipeline failed: {str(e)}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Print useful diagnostic information
    print(f"Current directory: {os.getcwd()}")
    
    # Check MongoDB connection first
    from db.mongo_client import MongoDBClient
    try:
        test_client = MongoDBClient()
        test_client.ping()
        print("MongoDB connection successful!")
    except Exception as e:
        print(f"ERROR: Cannot connect to MongoDB: {e}")
        print("Make sure MongoDB is running on localhost:27017")
        exit(1)
    
    # Run the pipeline
    runner = ETLPipelineRunner()
    runner.run_full_pipeline()

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
