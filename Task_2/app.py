from flask import Flask, request, render_template, jsonify
from index import search_index, fetch_suggestions

app = Flask(__name__) # Initialisiert die Flask-Anwendung

@app.route("/") # Definiert eine Route für die Startseite

def home():
    return render_template("home.html") # Rendert die HTML-Vorlage für die Startseite

@app.route("/search") # Definiert die Route für die Suchfunktion
def search():
    query = request.args.get("q", "").strip() # Holt die Suchanfrage aus den URL-Parametern und entfernt dabei Leerzeichen
    results = search_index(query) if query else []  # Führt die Suche nur aus, wenn eine Anfrage vorhanden ist
    return render_template("search.html", query=query, results=results) # Lädt die Seite mit den Suchergebnissen und übergibt die Daten

@app.route("/autocomplete") # Route für die Autovervollständigung
def autocomplete():
    prefix = request.args.get("prefix", "").strip() # Liefert Präfix für die Autovervollständigung und entfernt dabei Leerzeichen
    suggestions = fetch_suggestions(prefix) if prefix else [] # Liefert passende Vorschläge, wenn ein Präfix vorhanden ist
    return jsonify(suggestions)  # Gibt die Vorschläge als JSON zurück

if __name__ == "__main__":  # Startet die App nur, wenn das Skript direkt ausgeführt wird
    app.run(debug=False) # Führt die Flask-App aus, Debugging ist dabei deaktiviert
