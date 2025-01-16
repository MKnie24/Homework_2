from flask import Flask, request, render_template, jsonify
from index import search_index, fetch_suggestions

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    results = search_index(query) if query else []
    return render_template("search.html", query=query, results=results)

@app.route("/autocomplete")
def autocomplete():
    prefix = request.args.get("prefix", "").strip()
    suggestions = fetch_suggestions(prefix) if prefix else []
    return jsonify(suggestions)

if __name__ == "__main__":
    app.run(debug=True)
