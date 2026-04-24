#!/usr/bin/env python3
import sys
import os
import time
import logging
import signal

# Adds the parent directory (BiasLens) to the system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.collection_manager import CollectionManager
from clustering.clustering_service import ClusteringService
from biaslens.fact_extraction import cluster_fact_extraction


class ETLPipelineRunner:
    """Class to run the ETL pipeline for BiasLens"""

    def __init__(self):
        self.clustering_service = ClusteringService()

    def run_spider_direct(self):
        """Run the spider directly using Scrapy's crawl process"""
        from scrapy.crawler import CrawlerProcess
        from scrapy.utils.project import get_project_settings
        from biaslens.biaslens.spiders.BBCSpider import BBCSpider
        
        logging.info("Starting BBCSpider...")
        
        # Set up settings
        settings = get_project_settings()
        settings.set('MONGODB_URI', 'mongodb://localhost:27017')
        settings.set('MONGODB_DATABASE', 'biaslens')
        settings.set('LOG_LEVEL', 'INFO')
        
        # Make sure item pipeline is enabled
        settings.set('ITEM_PIPELINES', {
            'biaslens.biaslens.pipelines.MongoDBPipeline': 300,
        })
        
        # Create process and run spider
        process = CrawlerProcess(settings)
        
        try:
            # Add the spider
            process.crawl(BBCSpider)
            
            # Start the crawling - this will block until complete
            process.start()
            
            logging.info("BBCSpider completed successfully")
            return True
            
        except KeyboardInterrupt:
            logging.info("Spider interrupted by user")
            return False
        except Exception as e:
            logging.error(f"Spider failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            # Give time for MongoDB writes to complete
            time.sleep(2)

    def debug_check_articles(self):
        """Debug method to check what's in the database"""
        from db.collection_manager import CollectionManager
        
        cm = CollectionManager()
        
        print("\n" + "="*50)
        print("DATABASE DEBUG INFO")
        print("="*50)
        
        # Check all collections
        collections = cm.mongo_client.db.list_collection_names()
        print(f"Collections in database: {collections}")
        
        # Check articles collection
        article_count = cm.articles_collection.count_documents({})
        print(f"\nTotal articles in database: {article_count}")
        
        if article_count > 0:
            # Show a few sample articles
            samples = list(cm.articles_collection.find().limit(3))
            for i, sample in enumerate(samples, 1):
                print(f"\nSample {i}:")
                print(f"  Headline: {sample.get('headline', 'N/A')[:80]}")
                print(f"  Source: {sample.get('source', 'N/A')}")
                print(f"  URL: {sample.get('url', 'N/A')[:60]}")
        else:
            print("\n⚠️  WARNING: No articles found in database!")
            print("Possible issues:")
            print("  1. Spider didn't find any articles to scrape")
            print("  2. MongoDB pipeline not saving correctly")
            print("  3. Website structure may have changed")
            
        print("="*50 + "\n")
        return article_count

    def run_clustering(self):
        """Run clustering on all articles"""
        from db.collection_manager import CollectionManager
        
        collection_manager = CollectionManager()
        
        # Get all articles
        all_articles = list(collection_manager.articles_collection.find({}))
        
        logging.info(f"Running clustering on {len(all_articles)} articles")
        
        if len(all_articles) == 0:
            logging.warning("No articles found in database! Cannot run clustering.")
            return {}
        
        # Clear previous cluster collections
        self.clustering_service.clear_cluster_collections()
        
        # Process articles for clustering
        try:
            cluster_stats = self.clustering_service.process_new_articles(all_articles)
            logging.info(f"Clustering complete. Found {len(cluster_stats)} clusters")
            return cluster_stats
        except Exception as e:
            logging.error(f"Clustering failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}

    def run_fact_extraction(self):
        """Run fact extraction on clustered articles"""
        logging.info("Running fact extraction on clustered articles")
        from db.collection_manager import CollectionManager
        
        collection_manager = CollectionManager()
        
        # Get all cluster IDs
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
                # Get articles from main collection for this cluster
                articles_to_process = list(collection_manager.articles_collection.find(
                    {"cluster_id": cluster_id}
                ))
                
                if articles_to_process:
                    logging.info(f"Extracting facts from {len(articles_to_process)} articles in cluster {cluster_id}")
                    
                    # Ensure each article has content
                    for article in articles_to_process:
                        if "content" not in article or not article["content"]:
                            article["content"] = article.get("description", "")
                    
                    # Extract and store facts
                    cluster_fact_extraction.get_cluster_facts_and_store_in_mongo(
                        articles_to_process
                    )
                else:
                    logging.warning(f"No articles found for cluster {cluster_id}")
                    
            except Exception as e:
                logging.error(f"Error processing facts for cluster {cluster_id}: {str(e)}")
                import traceback
                traceback.print_exc()
        
        logging.info("Fact extraction completed")

    def run_full_pipeline(self):
        """Run the full ETL pipeline"""
        logging.info("="*50)
        logging.info("Starting full ETL pipeline")
        logging.info("="*50)
        
        try:
            # Step 1: Run the spider
            logging.info("\n[STEP 1/3] Running BBCSpider to collect articles...")
            spider_success = self.run_spider_direct()
            
            if not spider_success:
                logging.error("❌ Spider failed to run. Stopping pipeline.")
                return
            
            # Step 2: Check articles and run clustering
            logging.info("\n[STEP 2/3] Processing articles...")
            article_count = self.debug_check_articles()
            
            if article_count == 0:
                logging.error("❌ No articles found after spider run. Stopping pipeline.")
                return
            
            cluster_stats = self.run_clustering()
            
            if not cluster_stats:
                logging.warning("⚠️  No clusters created. Skipping fact extraction.")
                return
            
            # Step 3: Run fact extraction
            logging.info(f"\n[STEP 3/3] Running fact extraction on {len(cluster_stats)} clusters...")
            self.run_fact_extraction()
            
            logging.info("\n" + "="*50)
            logging.info("✅ ETL pipeline completed successfully!")
            logging.info(f"   - Articles scraped: {article_count}")
            logging.info(f"   - Clusters created: {len(cluster_stats)}")
            logging.info("="*50)
            
        except KeyboardInterrupt:
            logging.info("\n⚠️  Pipeline interrupted by user")
        except Exception as e:
            logging.error(f"❌ Pipeline failed: {str(e)}")
            import traceback
            traceback.print_exc()


def test_mongodb_connection():
    """Test MongoDB connection before running pipeline"""
    try:
        from db.mongo_client import MongoDBClient
        client = MongoDBClient()
        # Test connection by listing collections
        collections = client.db.list_collection_names()
        print(f"✅ MongoDB connection successful!")
        print(f"   Existing collections: {collections if collections else 'none'}")
        return True
    except Exception as e:
        print(f"❌ Cannot connect to MongoDB: {e}")
        print("   Make sure MongoDB is running: brew services start mongodb-community")
        return False


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    print("\n" + "="*50)
    print("BIASLENS ETL PIPELINE")
    print("="*50)
    print(f"Current directory: {os.getcwd()}")
    
    # Test MongoDB connection
    if not test_mongodb_connection():
        sys.exit(1)
    
    # Run the pipeline
    runner = ETLPipelineRunner()
    runner.run_full_pipeline()