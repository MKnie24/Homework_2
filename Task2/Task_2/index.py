from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID
from whoosh.qparser import QueryParser
from bs4 import BeautifulSoup
import os
import re
import string

def preprocess_content(content):
    import unicodedata #Für Normalisierung von Unicode-zeichen
    content = unicodedata.normalize("NFKC", content) #Damit Zeichen wie "é" als "e" genommen wird
    translator = str.maketrans("", "", string.punctuation) #Tabelle um Satzzeichen zu entfernen
    content = content.translate(translator) #Entfernt alle Satzzeichen aus dem Text
    lines = content.split("\n") #Teilt den Text in einzelne Zeilen auf
    unique_lines = list(dict.fromkeys([line.strip() for line in lines if line.strip()])) #Entfernt dopplete & leere Zeilen
    tokens = " ".join(unique_lines).lower().split() #Kombiniert die Zeilen und teilt die Wörter kleingeschrieben auf
    filtered_tokens = [token for token in tokens if token not in STOPWORDS] #Entfernt wörter wie "und" die in der Liste "StOPWORDS" stehen
    return " ".join(filtered_tokens) #Gibt den bereinigten Text als getrennte Wörter zurück


def generate_snippet(content, query, word_window=5, max_snippets=2):
    sentences = re.split(r'(?<=[.!?])\s+', content) #Teilt den Text in content in einzelne Sätze auf
    query_regex = re.compile(fr'({re.escape(query)})', re.IGNORECASE) #Erstellt ein Regex-Muster für die Suchanfrage in query, um diese im Text zu finden
    snippets = [] #Erstellt eine leere Liste, die gefundene Textauszüge zu speichert
    for sentence in sentences: #Iteriert durch jeden satz im Text
        if query.lower() in sentence.lower(): #Prüft ob die Suchanfrange im aktuellen Satz ist
            words = sentence.split() #Zerlegt den Satz in einzelne Wörter
            for i, word in enumerate(words): #Iteriert durch die Wörter des Satzes mit Index i
                if query.lower() in word.lower(): #Prüft ob die Suchanfrange im aktuellen Satz ist
                    start = max(0, i - word_window) #Berechnet den
                    end = min(len(words), i + word_window + 1) #Wählt eine begrenzte Anzahl an Wörter der Suchfrage aus für einen präzisen Kontext
                    highlighted = [query_regex.sub(r'<mark>\1</mark>', w) for w in words[start:end]] #Hebt die Suchanfrage in den Wörtern hervor
                    snippets.append(" ".join(highlighted)) #Fügt die hervorgehobene Wortgruppe als neuen Textauszug zur Liste "snippets" hinzu
                    break #Beendet die Suche sobald eine Übereinstimmung gefunden wurde
            if len(snippets) >= max_snippets:
                break
    return " ... ".join(snippets) if snippets else "No relevant snippet found."

def is_query_in_links(html_content, query):
    soup = BeautifulSoup(html_content, "html.parser")
    for anchor in soup.find_all("a"):
        if query.lower() in anchor.get_text().lower():
            return True
    for anchor in soup.find_all("a", href=True):
        if query.lower() in anchor["href"].lower():
            return True
    return False

def create_index(pages, index_dir="index"):
    if not os.path.exists(index_dir):
        os.makedirs(index_dir)
    schema = Schema(url=ID(stored=True, unique=True), content=TEXT(stored=True))
    ix = create_in(index_dir, schema)
    writer = ix.writer()
    for page in pages:
        preprocessed_content = preprocess_content(page["content"])
        if len(preprocessed_content.split()) < 10:
            continue
        writer.add_document(url=page["url"], content=preprocessed_content)
    writer.commit()

def fetch_suggestions(prefix, index_dir="autocomplete_index", limit=5):
    if not prefix.strip():
        return []
    try:
        ix = open_dir(index_dir)
    except Exception:
        return []
    qp = QueryParser("word", schema=ix.schema)
    q = qp.parse(f"{prefix.lower()}*")
    suggestions = []
    with ix.searcher() as searcher:
        hits = searcher.search(q, limit=limit)
        for hit in hits:
            suggestions.append(hit["word"])
    return suggestions

def search_index(query, index_dir="index", fuzzy=False):
    ix = open_dir(index_dir)
    qp = QueryParser("content", schema=ix.schema)
    phrases = re.findall(r'"(.*?)"', query)
    unquoted_words = re.sub(r'"(.*?)"', "", query).strip().split()
    query_parts = [f'"{phrase}"' for phrase in phrases]
    query_parts.extend(unquoted_words)
    parsed_query = qp.parse(" AND ".join(query_parts))
    results = []
    with ix.searcher() as searcher:
        hits = searcher.search(parsed_query, limit=10)
        for hit in hits:
            content = hit["content"]
            all_phrases_present = all(phrase.lower() in content.lower() for phrase in phrases)
            all_words_present = all(word.lower() in content.lower() for word in unquoted_words)
            if all_phrases_present and all_words_present:
                snippet = generate_snippet(content, query)
                if not is_query_in_links(content, query):
                    results.append({"url": hit["url"], "snippet": snippet})
    return results

STOPWORDS = {
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers", "it", "its", "itself", "they", "them", "their", "theirs", "themselves", "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as", "until", "while", "of", "at", "by", "for", "with", "about", "against", "between", "into", "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "any", "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now"
}
