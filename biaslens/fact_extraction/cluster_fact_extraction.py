import spacy
import re
from spacy.matcher import Matcher
from spacy.tokens import Span

# Load spaCy English model
nlp = spacy.load("en_core_web_sm")

# Preprocessing: remove extra characters, stopwords already handled by dependency parse


def clean_text(text):
    text = re.sub(r'\s+', ' ', text)  # remove multiple spaces
    text = re.sub(r'http\S+', '', text)  # remove URLs
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
        facts = extract_facts_with_ner(article['content'])
        for fact in facts:

            fact = {
                "article_id": article['id'],
                "cluster_id": article['cluster_id'],
                "source": article['source'],
                "fact": f"{fact['subject']} {fact['verb']} {fact['object']}",
            }

            collection.update_one(
                {"article_id": fact['article_id'], "fact": fact['fact'],
                    "cluster_id": fact['cluster_id'], "source": fact['source']},
                {"$set": fact},
                upsert=True
            )
