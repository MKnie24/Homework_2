from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID
from whoosh.qparser import QueryParser
from bs4 import BeautifulSoup
import os
import re
import string

def preprocess_content(content):
    import unicodedata # Für Normalisierung von Unicode-zeichen
    content = unicodedata.normalize("NFKC", content) # Damit Zeichen wie "é" als "e" genommen wird
    translator = str.maketrans("", "", string.punctuation) # Tabelle um Satzzeichen zu entfernen
    content = content.translate(translator) # Entfernt alle Satzzeichen aus dem Text
    lines = content.split("\n") # Teilt den Text in einzelne Zeilen auf
    unique_lines = list(dict.fromkeys([line.strip() for line in lines if line.strip()])) # Entfernt dopplete & leere Zeilen
    tokens = " ".join(unique_lines).lower().split() # Kombiniert die Zeilen und teilt die Wörter kleingeschrieben auf
    filtered_tokens = [token for token in tokens if token not in STOPWORDS] # Entfernt wörter wie "und" die in der Liste "StOPWORDS" stehen
    return " ".join(filtered_tokens) # Gibt den bereinigten Text als getrennte Wörter zurück


def generate_snippet(content, query, word_window=5, max_snippets=2): # Erstellt kurze Textauszüge, die die Suchanfrage im Kontext zeigen
    sentences = re.split(r'(?<=[.!?])\s+', content) # Teilt den Text in content in einzelne Sätze auf
    query_regex = re.compile(fr'({re.escape(query)})', re.IGNORECASE) # Erstellt ein Regex-Muster für die Suchanfrage in query, um diese im Text zu finden
    snippets = [] # Erstellt eine leere Liste, die gefundene Textauszüge zu speichert
    for sentence in sentences: #Iteriert durch jeden satz im Text
        if query.lower() in sentence.lower(): # Prüft ob die Suchanfrange im aktuellen Satz ist
            words = sentence.split() # Zerlegt den Satz in einzelne Wörter
            for i, word in enumerate(words): # Iteriert durch die Wörter des Satzes mit Index i
                if query.lower() in word.lower(): # Prüft ob die Suchanfrange im aktuellen Satz ist
                    start = max(0, i - word_window) # Berechnet den
                    end = min(len(words), i + word_window + 1) # Wählt eine begrenzte Anzahl an Wörter der Suchfrage aus für einen präzisen Kontext
                    highlighted = [query_regex.sub(r'<mark>\1</mark>', w) for w in words[start:end]] # Hebt die Suchanfrage in den Wörtern hervor
                    snippets.append(" ".join(highlighted)) # Fügt die hervorgehobene Wortgruppe als neuen Textauszug zur Liste "snippets" hinzu
                    break # Beendet die Suche sobald eine Übereinstimmung gefunden wurde
            if len(snippets) >= max_snippets: # Beendet die Schleife durch die Sätze, sobald die maximale Anzahl an Textauszügen erreicht wurde
                break
    return " ... ".join(snippets) if snippets else "No relevant snippet found." # Gibt die Textauszüge zurück, welche mit "..." getrennt werden

def is_query_in_links(html_content, query): # Prüft ob ein bestimmtes, gesuchtes Wort "query" in Links von HTML-Inhalten vorkommt
    soup = BeautifulSoup(html_content, "html.parser") # Lädt den Inhalt in "BeatifulSoup" hoch, um ihn zu analysieren
    for anchor in soup.find_all("a"): # Geht alle "a"s durch
        if query.lower() in anchor.get_text().lower(): # Prüft ob das gesuchte Wort im Text des Links vorkommt
            return True # Wenn Ja wird "wahr zurückgegeben"
    for anchor in soup.find_all("a", href=True): # Durchgeht alle Links
        if query.lower() in anchor["href"].lower(): # Überprüft ob das gesuchte Wort in der URL des Links vorkommt
            return True # Gibt "wahr" zurück wenn das gesuchte Wort in einer URL gefunden wurde
    return False # Gibt ansonsten "falsch" zurück

def create_index(pages, index_dir="index"): # Erstellt einen Index für die gegebenen Seiten
    if not os.path.exists(index_dir): # überprüft, ob das Indexverzeichnis existiert
        os.makedirs(index_dir) # Erstellt das Verzeichnis, falls es noch nicht exestiert
    schema = Schema(url=ID(stored=True, unique=True), content=TEXT(stored=True)) # Legt fest wie URL und Inhalt im Schema gespeichert werden
    ix = create_in(index_dir, schema) # Erstellt einen neuen Index im angegeben Verzeichnis
    writer = ix.writer() # Fügt die Seite als Dokument zum Index hinzu
    for page in pages: #Durchgeht alle Seiten in der Eingabeliste
        preprocessed_content = preprocess_content(page["content"]) # Bereinigt den Inhalt der Seite von Dingen wie: Stopwörtern, Sonderzeichen etc.
        if len(preprocessed_content.split()) < 10: # Überspringt Seiten mit weniger als 10 Wörtern
            continue
        writer.add_document(url=page["url"], content=preprocessed_content) # Fügt die Seite als Dokument zum Index hinzu.
    writer.commit()  # Speichert alle Dokumente Index und beendet den Schreibprozess

def fetch_suggestions(prefix, index_dir="autocomplete_index", limit=5): #Liefert Vorschläge basierend auf einem Präfix
    if not prefix.strip(): # Überprüft, ob Präfix leer ist
        return [] # Gibt eine leere Liste zurück, wenn kein Präfix vorhanden ist
    try:
        ix = open_dir(index_dir) # Öffnet Verzeichnis für den Autovervollständigungsindex
    except Exception: # Fängt Fehler ab, falls der Index nicht existiert oder nicht geöffnet werden kann
        return []  # Gibt eine leere Liste zurück, wenn ein Fehler auftritt
    qp = QueryParser("word", schema=ix.schema) # Erstellt einen "QueryParser" für das Feld "word" im Schema
    q = qp.parse(f"{prefix.lower()}*") # Erstellt eine Suchanfrage, um alle Wörter zu finden, die mit dem Präfix anfangen
    suggestions = [] # Erstellt eine leere Liste, um Vorschläge zu speichern
    with ix.searcher() as searcher: # Öffnet einen Suchprozess im Index
        hits = searcher.search(q, limit=limit) # Sucht nach Treffern basierend auf der Suchanfrage, dessen Anzahl durch "limit" begrenzt wird
        for hit in hits: # Iteriert durch alle Treffer
            suggestions.append(hit["word"]) # Fügt jedes gefundene Wort zur Vorschlagsliste hinzu
    return suggestions  #Gibt die Liste mit Vorschlägen zurück

def search_index(query, index_dir="index", fuzzy=False): # Sucht im Index nach einer Suchanfrage
    ix = open_dir(index_dir) # Öffnet das Verzeichnis für den Index
    qp = QueryParser("content", schema=ix.schema) # Erstellt einen QueryParser für das Feld "content" im Schema
    phrases = re.findall(r'"(.*?)"', query) # Extrahiert Wörter oder Phrasen in Anführungszeichen aus der Suchanfrage
    unquoted_words = re.sub(r'"(.*?)"', "", query).strip().split() # Entfernt Wörter in Anführungszeichen und teilt den Rest in einzelne Wörter
    query_parts = [f'"{phrase}"' for phrase in phrases] # # Fügt alle Phrasen (Anführungszeichen eingeschlossen) zur Suchanfrage hinzu
    query_parts.extend(unquoted_words) # Ergänzt die Suchanfrage um die nicht in Anführungszeichenstehenden Wörter
    parsed_query = qp.parse(" AND ".join(query_parts))  # Erstellt eine kombinierte Suchanfrage, die alle Teile enthält
    results = []  # Erstellt eine leere Liste, welche die Suchergebnisse speichert
    with ix.searcher() as searcher: # # Startet einen Suchprozess im Index
        hits = searcher.search(parsed_query, limit=10) # Führt die Suche aus, welche begrenzt ist auf maximal 10 Ergebnisse
        for hit in hits: # Geht alle Treffer durch
            content = hit["content"] # Liefert den Inhalt des aktuellen Treffers
            all_phrases_present = all(phrase.lower() in content.lower() for phrase in phrases) # Prüft ob alle Phrasen im Treffer enthalten sind
            all_words_present = all(word.lower() in content.lower() for word in unquoted_words) # Prüft ob alle Wörter im Treffer enthalten sind
            if all_phrases_present and all_words_present: # Wenn alle Phrasen und Wörter gefunden worden sind:
                snippet = generate_snippet(content, query) # Erstellt einen Textauszug mit der Suchanfrage
                if not is_query_in_links(content, query): # Prüft ob die Suchanfrage nicht in Links enthalten ist
                    results.append({"url": hit["url"], "snippet": snippet}) # Fügt die URL und den Textauszug zur Ergebnisliste hinzu
    return results # Gibt die Liste mit Suchergebnissen zurück

STOPWORDS = {
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers", "it", "its", "itself", "they", "them", "their", "theirs", "themselves", "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as", "until", "while", "of", "at", "by", "for", "with", "about", "against", "between", "into", "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "any", "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now"
}
