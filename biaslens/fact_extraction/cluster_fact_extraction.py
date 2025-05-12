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


def get_common_facts_across_sources(articles_and_headlines, similarity_threshold=0.8):
    """
    Extracts facts and returns only those referenced by multiple news sources.
    """
    source_fact_map = defaultdict(list)
    fact_texts = []

    for article in articles_and_headlines:
        facts = extract_facts_with_ner(article['content'])
        for fact in facts:
            fact_text = f"{fact['subject']} {fact['verb']} {fact['object']}"
            source_fact_map[article['source']].append(
                (fact_text, fact, article))
            fact_texts.append(fact_text)

    all_sources = list(source_fact_map.keys())
    all_facts = [fact for source_facts in source_fact_map.values()
                 for fact, _, _ in source_facts]
    unique_facts = list(set(all_facts))

    vectorizer = TfidfVectorizer().fit(unique_facts)
    tfidf_matrix = vectorizer.transform(unique_facts)

    common_facts_set = set()
    for i in range(len(unique_facts)):
        for j in range(i + 1, len(unique_facts)):
            sim = cosine_similarity(tfidf_matrix[i], tfidf_matrix[j])[0][0]
            if sim >= similarity_threshold:
                fact1_sources = {src for src, facts in source_fact_map.items()
                                 if any(f[0] == unique_facts[i] for f in facts)}
                fact2_sources = {src for src, facts in source_fact_map.items()
                                 if any(f[0] == unique_facts[j] for f in facts)}
                if len(fact1_sources.union(fact2_sources)) > 1:
                    common_facts_set.add(unique_facts[i])
                    common_facts_set.add(unique_facts[j])

    common_facts = []
    for source in source_fact_map:
        for fact_text, fact, article in source_fact_map[source]:
            if fact_text in common_facts_set:
                fact['article'] = article
                common_facts.append(fact)

    with open('common_facts.txt', 'w') as f:
        for fact in common_facts:
            f.write(f"{fact['subject']} {fact['verb']} {fact['object']}\n")
    return common_facts


# Dummy articles


def get_cluster_facts_and_store_in_mongo(articles_and_headlines):
    """
    Given a list of articles, extract facts and store them in MongoDB.
    """
    # Connect to MongoDB
    from pymongo import MongoClient
    client = MongoClient('mongodb://localhost:27017/')
    db = client['biaslens']
    collection = db['facts']

    for article in articles_and_headlines:
        # common_facts = get_common_facts_across_sources(articles_and_headlines)
        # facts = extract_facts_with_ner(article['content'])
        facts = get_common_facts_across_sources(articles_and_headlines)
        for fact in facts:

            fact_to_store = {

                "subject": fact['subject'],
                "verb": fact['verb'],
                "object": fact['object'],
                "article_id": article['id'],
                "cluster_id": article['cluster_id'],
                "source": article['source'],
                "timestamp": article.get('published_date')

            }
            logging.info(f"Fact to store: {fact_to_store}")
            # Check if the fact already exists in the database
            existing_fact = collection.find_one({
                "subject": fact['subject'],
                "verb": fact['verb'],
                "object": fact['object'],
                "article_id": article['id']
            })
            if existing_fact:
                logging.info(f"Fact already exists: {existing_fact}")
                continue
            # Check if the fact is empty
            if not fact_to_store['subject'] or not fact_to_store['verb'] or not fact_to_store['object']:
                logging.info(f"Fact is empty: {fact_to_store}")
                continue

            # Insert fact into MongoDB
            try:
                collection.insert_one(fact_to_store)
                facts_inserted_count += 1
            except Exception as e:
                # Consider adding logging here if you have a logger instance
                logging.info(f"Error inserting fact into MongoDB: {e}")
                logging.info(f"Problematic fact: {fact_to_store}")

    client.close()
