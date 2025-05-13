# import numpy as np
# import pandas as pd
# from sentence_transformers import SentenceTransformer
# from sklearn.cluster import DBSCAN
# from sklearn.metrics.pairwise import cosine_similarity
# import logging


# class ArticleClustering:
#     """Class for clustering news articles based on their content"""

#     def __init__(self, eps=0.5, min_samples=1, model_name='all-MiniLM-L6-v2'):
#         """
#         Initialize clustering model

#         Args:
#             eps (float): DBSCAN epsilon parameter
#             min_samples (int): DBSCAN min_samples parameter
#             model_name (str): SentenceTransformer model name
#         """
#         self.eps = eps
#         self.min_samples = min_samples
#         logging.info(f"Loading sentence transformer model: {model_name}")
#         self.model = SentenceTransformer(model_name)
#         self.dbscan = DBSCAN(metric='cosine', eps=self.eps,
#                              min_samples=self.min_samples)

#     def _prepare_text(self, articles):
#         """Prepare text for embedding"""
#         texts = []
#         for article in articles:
#             # Combine headline and description for better clustering
#             headline = article.get("headline", "")
#             description = article.get("description", "")
#             # content_preview = article.get("content", "")[
#             #     :200] if article.get("content") else ""

#             # Combine all text fields
#             combined_text = f"{headline} {description}".strip()
#             texts.append(combined_text)
#         return texts

#     def cluster_articles(self, articles):
#         """
#         Cluster articles based on content similarity

#         Args:
#             articles: List of article dictionaries

#         Returns:
#             DataFrame with articles and their assigned clusters
#         """
#         if not articles:
#             logging.warning("No articles provided for clustering")
#             return pd.DataFrame()

#         logging.info(f"Clustering {len(articles)} articles")

#         # Prepare text data
#         texts = self._prepare_text(articles)

#         # Create dataframe
#         df = pd.DataFrame({
#             'text': texts,
#             'article': articles
#         })

#         # Generate embeddings
#         logging.info("Creating embeddings...")
#         embeddings = self.model.encode(
#             df['text'].tolist(), show_progress_bar=True)

#         # Perform clustering
#         logging.info("Applying DBSCAN clustering...")
#         df['cluster'] = self.dbscan.fit_predict(embeddings)

#         # Count clusters
#         num_clusters = len(set(df['cluster'])) - \
#             (1 if -1 in df['cluster'].unique() else 0)
#         logging.info(f"Number of event clusters found: {num_clusters}")

#         return df

# import numpy as np
# import pandas as pd
# import logging
# from sklearn.feature_extraction.text import TfidfVectorizer
# from sklearn.cluster import AgglomerativeClustering
# from sklearn.metrics.pairwise import cosine_distances
# from sklearn.pipeline import make_pipeline
# from sklearn.preprocessing import Normalizer
# import re
# import string


# class ArticleClustering:
#     """Class for clustering news articles based on headlines"""

#     def __init__(self, distance_threshold=0.7, ngram_range=(1, 2), stop_words='english'):
#         """
#         Initialize clustering parameters

#         Args:
#             distance_threshold (float): Threshold to determine clusters
#             ngram_range (tuple): N-gram range for TF-IDF
#             stop_words (str): Stop words to remove
#         """
#         self.distance_threshold = distance_threshold
#         self.ngram_range = ngram_range
#         self.stop_words = stop_words
#         self.vectorizer = TfidfVectorizer(
#             ngram_range=self.ngram_range, stop_words=self.stop_words)
#         self.normalizer = Normalizer(copy=False)

#     def _preprocess_text(self, text):
#         text = text.lower()
#         text = re.sub(r'\s+', ' ', text)
#         text = text.translate(str.maketrans('', '', string.punctuation))
#         return text.strip()

#     def _prepare_text(self, articles):
#         return [self._preprocess_text(article.get("headline", "")) for article in articles]

#     def cluster_articles(self, articles):
#         if not articles:
#             logging.warning("No articles provided for clustering")
#             return pd.DataFrame()

#         logging.info(f"Clustering {len(articles)} articles")

#         # Prepare and preprocess headlines
#         texts = self._prepare_text(articles)

#         # Create DataFrame
#         df = pd.DataFrame({
#             'text': texts,
#             'article': articles
#         })

#         # TF-IDF Vectorization
#         logging.info("Creating TF-IDF vectors...")
#         tfidf_matrix = self.vectorizer.fit_transform(df['text'])
#         tfidf_matrix = self.normalizer.transform(tfidf_matrix)

#         # Agglomerative Clustering
#         logging.info("Applying Agglomerative Clustering...")
#         clustering = AgglomerativeClustering(
#             affinity='euclidean',
#             linkage='average',
#             distance_threshold=self.distance_threshold,
#             n_clusters=None
#         )
#         df['cluster'] = clustering.fit_predict(tfidf_matrix.toarray())

#         num_clusters = len(set(df['cluster']))
#         logging.info(f"Number of headline clusters found: {num_clusters}")

#         return df

import matplotlib.pyplot as plt
import seaborn as sns
from scipy.cluster.hierarchy import dendrogram, linkage
from sklearn.preprocessing import normalize
import numpy as np
import pandas as pd
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import AgglomerativeClustering
import re
import string


class ArticleClustering:
    """Class for clustering news articles based on headlines"""

    def __init__(self, distance_threshold=1.5, ngram_range=(1, 2), stop_words='english'):
        self.distance_threshold = distance_threshold
        self.ngram_range = ngram_range
        self.stop_words = stop_words
        self.vectorizer = TfidfVectorizer(
            ngram_range=self.ngram_range, stop_words=self.stop_words)

    def _preprocess_text(self, text):
        text = text.lower()
        text = re.sub(r'\s+', ' ', text)
        text = text.translate(str.maketrans('', '', string.punctuation))
        return text.strip()

    def _prepare_text(self, articles):
        return [self._preprocess_text(article.get("headline", "")) for article in articles]

    def cluster_articles(self, articles):
        if not articles:
            logging.warning("No articles provided for clustering")
            return pd.DataFrame()

        logging.info(f"Clustering {len(articles)} articles")

        texts = self._prepare_text(articles)
        df = pd.DataFrame({'text': texts, 'article': articles})

        logging.info("Creating TF-IDF vectors...")
        tfidf_matrix = self.vectorizer.fit_transform(df['text'])

        logging.info("Applying Agglomerative Clustering...")
        clustering = AgglomerativeClustering(
            # affinity='euclidean',
            linkage='ward',
            distance_threshold=self.distance_threshold,
            n_clusters=None
        )
        df['cluster'] = clustering.fit_predict(tfidf_matrix.toarray())

        num_clusters = len(set(df['cluster']))
        logging.info(f"Number of headline clusters found: {num_clusters}")

        return df

    def visualize_clusters_with_dendrogram_and_heatmap(self, articles):
        """
        Generates a dendrogram and TF-IDF heatmap using the ArticleClustering instance.

        Args:
            model (ArticleClustering): Instance of the ArticleClustering class.
            articles (list): List of article dictionaries with 'headline' keys.
        """
        if not articles:
            print("No articles provided.")
            return

        # Preprocess and vectorize text
        texts = self._prepare_text(articles)
        tfidf_matrix = self.vectorizer.fit_transform(texts).toarray()
        feature_names = self.vectorizer.get_feature_names_out()

        tfidf_matrix_norm = normalize(tfidf_matrix)

        # --- Dendrogram ---
        plt.figure(figsize=(10, 6))
        linkage_matrix = linkage(tfidf_matrix_norm, method='ward')
        dendrogram(linkage_matrix, labels=[
                   f"Article {i+1}" for i in range(len(texts))], leaf_rotation=90)
        plt.title("Agglomerative Clustering Dendrogram")
        plt.xlabel("Articles")
        plt.ylabel("Distance")
        plt.tight_layout()
        plt.show()

        # --- Heatmap ---
        plt.figure(figsize=(12, max(6, len(articles) * 0.4)))
        sns.heatmap(
            pd.DataFrame(tfidf_matrix_norm, columns=feature_names),
            cmap='YlGnBu',
            xticklabels=True,
            yticklabels=[f"Article {i+1}" for i in range(len(texts))]
        )
        plt.title("TF-IDF Heatmap")
        plt.xlabel("TF-IDF Features")
        plt.ylabel("Articles")
        plt.tight_layout()
        plt.show()

    # Instantiate your clustering model
    # model = ArticleClustering(distance_threshold=1.5)

    # # Cluster the articles
    # clustered_df = model.cluster_articles(articles)

    # # Visualize the clusters and TF-IDF importance
    # visualize_clusters_with_dendrogram_and_heatmap(model, articles)
