import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os

def extract_clean_content(html):  # Extrahiert den bereinigten Textinhalt aus HTML
    soup = BeautifulSoup(html, "html.parser") # Parst den HTML-Inhalt
    for script_or_style in soup(["script", "style"]): # Entfernt JavaScript und CSS-Abschnitte
        script_or_style.extract()
    for anchor in soup.find_all("a"):  # Entfernt alle Links
        anchor.extract()
    text = soup.get_text(separator="\n", strip=True) # Liefert den Textinhalt der Seite, Zeilen werden getrennt
    return "\n".join(line.strip() for line in text.splitlines() if line.strip()) # Gibt nur nicht-leere Zeilen zurück

def crawl(base_url, domain_restrict, max_pages=1000):  # Crawlt eine Website und sammelt Seiteninhalte
    crawled = set() # Speichert bereits besuchte URLs
    to_crawl = {base_url} # Speichert URLs, die noch besucht werden sollen
    pages = [] # Speichert die gecrawlten Seiten mit URL und Inhalt

    while to_crawl and (max_pages is None or len(crawled) < max_pages): #Läuft weiter, solange es URLs zu crawlen gibt und das Limit nicht erreicht wurde
        url = to_crawl.pop()  #Entnimmt eine URL aus der Liste der zu crawlenden URLs
        if url in crawled: # Überspringt die URL, wenn sie bereits besucht wurde
            continue
        try:
            response = requests.get(url) # Sendet eine HTTP-GET-Anfrage an die URL
            if response.status_code == 200 and "text/html" in response.headers.get("Content-Type", ""): # Prüft, ob die Seite HTML-Inhalt hat
                crawled.add(url) # Markiert die URL als bereits "crawled"
                content = extract_clean_content(response.text) # Holt den bereinigten Textinhalt der Seite
                if content: # Speichert die Seite nur, wenn die Seite Inhalt hat
                    pages.append({"url": url, "content": content}) # Speichert die URL und den bereinigten Inhalt der Seite in der Liste "pages"
                soup = BeautifulSoup(response.text, 'html.parser') # Parst den HTML-Inhalt der Seite
                for link in soup.find_all('a', href=True): # Findet alle Links auf der Seite
                    absolute_url = urljoin(url, link['href']) # Wandelt relative Links in absolute URLs um
                    if absolute_url.startswith(f"https://{domain_restrict}") and absolute_url not in crawled and absolute_url not in to_crawl: # Prüft, ob die URL zur eingeschränkten Domain gehört, noch nicht besucht wurde und noch nicht zur Crawl-Liste gehört
                        to_crawl.add(absolute_url) # Fügt neue URLs hinzu, die noch nicht besucht wurden
        except Exception as e: # Fängt Fehler ab, wie Verbindungsprobleme
            print(f"Error crawling {url}: {e}") # Gibt die Fehler aus
    return pages # Gibt die Liste der gecrawlten Seiten mit URL und Inhalt zurück

if __name__ == "__main__": # Führt den Code nur aus, wenn das Skript direkt aufgerufen wird
    base_url = "https://www.uni-osnabrueck.de" # Start-URL für das "Crawlen"
    domain_restrict = "www.uni-osnabrueck.de" # Beschränkt das "Crawlen" auf diese Domain
    pages = crawl(base_url, domain_restrict) # Startet den "Crawl-Prozess"
    os.makedirs("data", exist_ok=True) # Erstellt das Verzeichnis "data", falls es nicht existiert
    with open("data/crawled_pages.txt", "w", encoding="utf-8") as f: # Öffnet eine Datei, um die "gecrawlten" Seiten zu speichern
        for page in pages:  # Iteriert durch alle "gecrawlten" Seiten
            f.write(f"URL: {page['url']}\n\n") # Schreibt die URL der Seite in die Datei
            f.write(f"Content:\n{page['content']}\n") # Schreibt den Inhalt der Seite in die Datei
            f.write("-" * 80 + "\n\n") # Fügt eine Trennlinie zwischen den Seiten hinzu
