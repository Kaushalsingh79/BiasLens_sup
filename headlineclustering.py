import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
import string
import pandas as pd
import numpy as np
import nltk

nltk.download('stopwords')
nltk.download('punkt_tab')


# Load Data (Assuming headlines are in a list)
headlines = ["Govt announces new policy",
             "Stock market sees sharp decline", "Sports team wins championship"]

# Preprocessing Function
stop_words = set(stopwords.words('english'))


def preprocess(text):
    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    tokens = word_tokenize(text)
    tokens = [word for word in tokens if word not in stop_words]
    return " ".join(tokens)


# Preprocess Headlines
cleaned_headlines = [preprocess(headline) for headline in headlines]

# Vectorization using TF-IDF
vectorizer = TfidfVectorizer(max_features=5000)
X = vectorizer.fit_transform(cleaned_headlines)

# Clustering using K-Means
num_clusters = 5  # Adjust based on data
kmeans = KMeans(n_clusters=num_clusters, random_state=42)
clusters = kmeans.fit_predict(X)

# Add Cluster Labels to DataFrame
df = pd.DataFrame({"headline": headlines, "cluster": clusters})

# Visualize Clusters (Using PCA for dimensionality reduction)
pca = PCA(n_components=2)
reduced_X = pca.fit_transform(X.toarray())
plt.scatter(reduced_X[:, 0], reduced_X[:, 1],
            c=clusters, cmap='viridis', alpha=0.5)
plt.title("News Headline Clusters")
plt.show()

# Display Clustered Headlines
for i in range(num_clusters):
    print(f"\nCluster {i}:")
    print(df[df['cluster'] == i]['headline'].tolist())
