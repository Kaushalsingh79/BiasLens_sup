import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.feature_extraction.text import TfidfVectorizer
from collections import defaultdict
from sklearn.metrics.pairwise import cosine_similarity
import spacy
import re
from spacy.matcher import Matcher
from spacy.tokens import Span
import logging
# Load spaCy English model
nlp = spacy.load("en_core_web_sm")

# Preprocessing: remove extra characters, stopwords already handled by dependency parse


def clean_text(text):
    text = re.sub(r'\s+', ' ', text)  # remove multiple spaces
    text = re.sub(r'http\S+', '', text)  # remove URLs
    text = re.sub(r'<[^<]+?>', '', text)  # remove HTML tags
    return text.strip()

# Function to extract subject-verb-object triples


def extract_facts_with_ner(text):
    doc = nlp(clean_text(text))
    facts = []

    for sent in doc.sents:
        for token in sent:
            if token.dep_ == 'ROOT' and token.pos_ in ['VERB', 'AUX']:
                # Identifying subject
                subject = [w for w in token.lefts if w.dep_ in [
                    'nsubj',         # nominal subject
                    'nsubjpass',     # passive nominal subject
                    'csubj',         # clausal subject
                    'csubjpass',     # clausal passive subject
                    'agent',         # agent in passive construction
                    # expletive subject (e.g. "it" in "it is raining")
                    'expl'
                ]]

                # Identifying object
                obj = [w for w in token.rights if w.dep_ in [
                    'dobj',          # direct object
                    'iobj',          # indirect object
                    'attr',          # attribute
                    'prep',          # prepositional object root
                    'pobj',          # object of a preposition
                    'xcomp',         # open clausal complement
                    'acomp',         # adjectival complement
                    'dative',        # dative object
                    'oprd',          # object predicate
                    'obj',           # general object (used in some UD schemes)
                    'obl',           # oblique nominal
                    'nmod',          # nominal modifier
                    'npadvmod',      # noun phrase adverbial modifier
                    'advcl'          # adverbial clause modifier
                ]]

                if subject and obj:
                    sub_span = subject[0].subtree
                    obj_span = obj[0].subtree

                    # Adding the extracted facts
                    facts.append({
                        "subject": " ".join(w.text for w in sub_span),
                        "verb": token.text,
                        "object": " ".join(w.text for w in obj_span)
                    })

    # Entity resolution for pronouns like "son", "he", etc.
    resolved_facts = []
    for fact in facts:
        subj_doc = nlp(fact['subject'])
        ent_match = None
        for ent in doc.ents:
            # Matching specific entities with custom lists or NER
            if fact['subject'].lower() in [
                # Pronouns - personal
                'he', 'she', 'they', 'him', 'her', 'them', 'his', 'hers', 'their', 'theirs',

                # Pronouns - demonstrative
                'this', 'that', 'these', 'those',

                # Family relationships
                'son', 'daughter', 'father', 'mother', 'brother', 'sister',
                'husband', 'wife', 'uncle', 'aunt', 'nephew', 'niece',
                'grandfather', 'grandmother', 'grandson', 'granddaughter',

                # Generic persons/roles
                'man', 'woman', 'child', 'person', 'people', 'individual', 'group',
                'leader', 'official', 'president', 'prime minister', 'minister',
                'commander', 'general', 'soldier', 'spokesperson', 'representative',
                'protester', 'activist', 'journalist', 'reporter', 'analyst',

                # Titles and positions
                'mr', 'mrs', 'ms', 'dr', 'sir', 'madam',
                'chairman', 'chairwoman', 'ceo', 'director', 'head',

                # Organizations (used as ambiguous referrers sometimes)
                'government', 'administration', 'authority', 'regime', 'military', 'intelligence',
                'agency', 'forces', 'department', 'bureau', 'council', 'committee',

                # Other common referential terms
                'entity', 'organization', 'body', 'institution', 'office',
                'side', 'party', 'group', 'faction', 'team', 'company',

                # Abstract referents
                'source', 'insider', 'officials', 'eyewitnesses', 'locals', 'authorities'
            ] and ent.label_ in ['PERSON', 'ORG']:
                ent_match = ent.text
                break
        resolved_facts.append({
            "subject": ent_match if ent_match else fact['subject'],
            "verb": fact['verb'],
            "object": fact['object']
        })

    return resolved_facts


# def get_common_facts_across_sources(articles_and_headlines, similarity_threshold=0.8):
#     """
#     Extracts facts and returns only those referenced by multiple news sources.
#     """
#     source_fact_map = defaultdict(list)
#     fact_texts = []

#     for article in articles_and_headlines:
#         facts = extract_facts_with_ner(article['content'])
#         for fact in facts:
#             fact_text = f"{fact['subject']} {fact['verb']} {fact['object']}"
#             source_fact_map[article['source']].append(
#                 (fact_text, fact, article))
#             fact_texts.append(fact_text)

#     all_sources = list(source_fact_map.keys())
#     all_facts = [fact for source_facts in source_fact_map.values()
#                  for fact, _, _ in source_facts]
#     unique_facts = list(set(all_facts))

#     vectorizer = TfidfVectorizer().fit(unique_facts)
#     tfidf_matrix = vectorizer.transform(unique_facts)

#     common_facts_set = set()
#     for i in range(len(unique_facts)):
#         for j in range(i + 1, len(unique_facts)):
#             sim = cosine_similarity(tfidf_matrix[i], tfidf_matrix[j])[0][0]
#             if sim >= similarity_threshold:
#                 fact1_sources = {src for src, facts in source_fact_map.items()
#                                  if any(f[0] == unique_facts[i] for f in facts)}
#                 fact2_sources = {src for src, facts in source_fact_map.items()
#                                  if any(f[0] == unique_facts[j] for f in facts)}
#                 if len(fact1_sources.union(fact2_sources)) > 1:
#                     common_facts_set.add(unique_facts[i])
#                     common_facts_set.add(unique_facts[j])

#     common_facts = []
#     for source in source_fact_map:
#         for fact_text, fact, article in source_fact_map[source]:
#             if fact_text in common_facts_set:
#                 fact['article'] = article
#                 common_facts.append(fact)

#     with open('common_facts.txt', 'w') as f:
#         for fact in common_facts:
#             f.write(f"{fact['subject']} {fact['verb']} {fact['object']}\n")
#     return common_facts


def get_common_facts_in_cluster(cluster_facts, similarity_threshold=0.5):
    """
    Returns common facts from a single cluster based on similarity of subject-verb-object strings.
    """
    fact_text_map = {}
    fact_texts = []

    for fact in cluster_facts:
        fact_text = f"{fact['subject']} {fact['verb']} {fact['object']}"
        fact_texts.append(fact_text)
        fact_text_map[fact_text] = fact

    vectorizer = TfidfVectorizer().fit(fact_texts)
    tfidf_matrix = vectorizer.transform(fact_texts)

    common_fact_indices = set()
    for i in range(len(fact_texts)):
        for j in range(i + 1, len(fact_texts)):
            sim = cosine_similarity(tfidf_matrix[i], tfidf_matrix[j])[0][0]
            if sim >= similarity_threshold:
                common_fact_indices.add(i)
                common_fact_indices.add(j)

    common_facts = [fact_text_map[fact_texts[i]] for i in common_fact_indices]

    with open('common_facts_cluster.txt', 'w') as f:
        for fact in common_facts:
            f.write(f"{fact['subject']} {fact['verb']} {fact['object']}\n")
    return common_facts

# Dummy articles


def get_cluster_facts_and_store_in_mongo(articles_and_headlines):
    """
    Given a list of articles for a cluster, extract facts, find common ones, and store them in MongoDB.
    """
    from pymongo import MongoClient  # Keep import here if not at module level
    client = MongoClient('mongodb://localhost:27017/')
    db = client['biaslens']
    facts_collection = db['facts']  # Renamed for clarity
    facts_inserted_count = 0

    all_facts_from_cluster_articles = []

    # Step 1: Extract facts from each article and add metadata
    for article_data in articles_and_headlines:
        if 'content' not in article_data or not article_data['content']:
            logging.warning(
                f"Article ID {article_data.get('id', 'Unknown')} in cluster {article_data.get('cluster_id')} has no content, skipping fact extraction for this article.")
            continue

        try:
            individual_article_facts = extract_facts_with_ner(
                article_data['content'])
            for fact in individual_article_facts:
                # Add metadata from the article to each fact
                fact['article_id'] = article_data.get(
                    'id')  # This comes from _id
                fact['cluster_id'] = article_data.get('cluster_id')
                fact['source'] = article_data.get('source')
                # Ensure 'published_date' is consistently available
                fact['timestamp'] = article_data.get('published_date')
                all_facts_from_cluster_articles.append(fact)
        except Exception as e:
            logging.error(
                f"Error extracting facts from article ID {article_data.get('id', 'Unknown')} in cluster {article_data.get('cluster_id')}: {e}")
            continue  # Skip to the next article if fact extraction fails for one

    if not all_facts_from_cluster_articles:
        logging.warning(
            f"No facts were extracted from any articles in cluster {articles_and_headlines[0].get('cluster_id') if articles_and_headlines else 'Unknown'}. Nothing to process further.")
        client.close()
        return

    # Step 2: Find common facts among all extracted facts for this cluster
    # get_common_facts_in_cluster expects a list of fact dictionaries and returns a subset of them.
    common_facts_to_store = get_common_facts_in_cluster(
        all_facts_from_cluster_articles)

    current_cluster_id_for_logging = articles_and_headlines[0].get(
        'cluster_id') if articles_and_headlines else "Unknown"
    logging.info(
        f"Found {len(common_facts_to_store)} common facts to potentially store for cluster {current_cluster_id_for_logging}.")

    # Step 3: Store the common facts
    for fact_data in common_facts_to_store:  # fact_data is a dictionary that should contain s,v,o and metadata
        # Ensure essential keys are present in the fact dictionary
        if not all(k in fact_data for k in ['subject', 'verb', 'object']):
            logging.warning(
                f"Common fact is missing SVO components: {fact_data}. Skipping.")
            continue

        if not fact_data.get('subject') or not fact_data.get('verb') or not fact_data.get('object'):
            logging.info(f"Common fact has empty SVO: {fact_data}. Skipping.")
            continue

        # Prepare document for MongoDB, ensuring all fields are present
        fact_doc_to_insert = {
            "subject": fact_data['subject'],
            "verb": fact_data['verb'],
            "object": fact_data['object'],
            # Should be present from Step 1
            "article_id": fact_data.get('article_id'),
            # Should be present from Step 1
            "cluster_id": fact_data.get('cluster_id'),
            # Should be present from Step 1
            "source": fact_data.get('source'),
            # Should be present from Step 1
            "timestamp": fact_data.get('timestamp')
        }

        # Check if the fact already exists
        try:
            existing_fact = facts_collection.find_one({
                "subject": fact_doc_to_insert["subject"],
                "verb": fact_doc_to_insert["verb"],
                "object": fact_doc_to_insert["object"],
                # Use specific article_id for uniqueness
                "article_id": fact_doc_to_insert["article_id"],
                "cluster_id": fact_doc_to_insert["cluster_id"]
            })

            if existing_fact:
                logging.debug(
                    f"Fact already exists, skipping: {fact_doc_to_insert['subject']}|{fact_doc_to_insert['verb']}|{fact_doc_to_insert['object']} from article {fact_doc_to_insert['article_id']}")
                continue

            facts_collection.insert_one(fact_doc_to_insert)
            facts_inserted_count += 1
        except Exception as e:
            logging.error(
                f"Error inserting fact into MongoDB for cluster {current_cluster_id_for_logging}: {e}")
            logging.error(f"Problematic fact data: {fact_doc_to_insert}")

    logging.info(
        f"Inserted {facts_inserted_count} new common facts for cluster {current_cluster_id_for_logging}.")
    client.close()


def visualize_article_and_fact_word_counts(articles_and_headlines):
    """
    Visualizes the total number of words in the article content + headline vs. the total number of words in extracted facts.
    """

    article_ids = []
    content_word_counts = []
    headline_word_counts = []
    fact_word_counts = []

    for article in articles_and_headlines:
        article_id = article.get("id", "Unknown")
        content = article.get("content", "")
        headline = article.get("headline", "")

        total_content_words = len(clean_text(content).split())
        total_headline_words = len(clean_text(headline).split())

        facts = extract_facts_with_ner(content)
        total_fact_words = sum(
            len(fact['subject'].split()) +
            len(fact['verb'].split()) + len(fact['object'].split())
            for fact in facts
        )

        article_ids.append(str(article_id))
        content_word_counts.append(total_content_words)
        headline_word_counts.append(total_headline_words)
        fact_word_counts.append(total_fact_words)

    # Plotting
    plt.figure(figsize=(14, 6))
    x = range(len(article_ids))

    plt.bar(x, content_word_counts, label='Content Words', color='skyblue')
    plt.bar(x, headline_word_counts, bottom=content_word_counts,
            label='Headline Words', color='dodgerblue')
    plt.bar(x, fact_word_counts, label='Fact Words', color='orange', alpha=0.8)

    plt.xticks(x, article_ids, rotation=45, ha='right')
    plt.ylabel("Word Count")
    plt.title("Word Count Comparison: Content + Headline vs Extracted Facts")
    plt.legend()
    plt.tight_layout()
    plt.show()
