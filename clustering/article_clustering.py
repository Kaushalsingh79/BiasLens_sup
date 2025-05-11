import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity
import logging


class ArticleClustering:
    """Class for clustering news articles based on their content"""

    def __init__(self, eps=0.3, min_samples=1, model_name='all-MiniLM-L6-v2'):
        """
        Initialize clustering model

        Args:
            eps (float): DBSCAN epsilon parameter
            min_samples (int): DBSCAN min_samples parameter
            model_name (str): SentenceTransformer model name
        """
        self.eps = eps
        self.min_samples = min_samples
        logging.info(f"Loading sentence transformer model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.dbscan = DBSCAN(metric='cosine', eps=self.eps,
                             min_samples=self.min_samples)

    def _prepare_text(self, articles):
        """Prepare text for embedding"""
        texts = []
        for article in articles:
            # Combine headline and description for better clustering
            headline = article.get("headline", "")
            description = article.get("description", "")
            # content_preview = article.get("content", "")[
            #     :200] if article.get("content") else ""

            # Combine all text fields
            combined_text = f"{headline} {description}".strip()
            texts.append(combined_text)
        return texts

    def cluster_articles(self, articles):
        """
        Cluster articles based on content similarity

        Args:
            articles: List of article dictionaries

        Returns:
            DataFrame with articles and their assigned clusters
        """
        if not articles:
            logging.warning("No articles provided for clustering")
            return pd.DataFrame()

        logging.info(f"Clustering {len(articles)} articles")

        # Prepare text data
        texts = self._prepare_text(articles)

        # Create dataframe
        df = pd.DataFrame({
            'text': texts,
            'article': articles
        })

        # Generate embeddings
        logging.info("Creating embeddings...")
        embeddings = self.model.encode(
            df['text'].tolist(), show_progress_bar=True)

        # Perform clustering
        logging.info("Applying DBSCAN clustering...")
        df['cluster'] = self.dbscan.fit_predict(embeddings)

        # Count clusters
        num_clusters = len(set(df['cluster'])) - \
            (1 if -1 in df['cluster'].unique() else 0)
        logging.info(f"Number of event clusters found: {num_clusters}")

        return df
