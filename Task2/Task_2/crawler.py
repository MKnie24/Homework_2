import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os

def extract_clean_content(html):
    soup = BeautifulSoup(html, "html.parser")
    for script_or_style in soup(["script", "style"]):
        script_or_style.extract()
    for anchor in soup.find_all("a"):
        anchor.extract()
    text = soup.get_text(separator="\n", strip=True)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())

def crawl(base_url, domain_restrict, max_pages=None):
    crawled = set()
    to_crawl = {base_url}
    pages = []

    while to_crawl and (max_pages is None or len(crawled) < max_pages):
        url = to_crawl.pop()
        if url in crawled:
            continue
        try:
            response = requests.get(url)
            if response.status_code == 200 and "text/html" in response.headers.get("Content-Type", ""):
                crawled.add(url)
                content = extract_clean_content(response.text)
                if content:
                    pages.append({"url": url, "content": content})
                soup = BeautifulSoup(response.text, 'html.parser')
                for link in soup.find_all('a', href=True):
                    absolute_url = urljoin(url, link['href'])
                    if absolute_url.startswith(f"https://{domain_restrict}") and absolute_url not in crawled and absolute_url not in to_crawl:
                        to_crawl.add(absolute_url)
        except Exception as e:
            print(f"Error crawling {url}: {e}")
    return pages

if __name__ == "__main__":
    base_url = "https://www.uni-osnabrueck.de"
    domain_restrict = "www.uni-osnabrueck.de"
    pages = crawl(base_url, domain_restrict)
    os.makedirs("data", exist_ok=True)
    with open("data/crawled_pages.txt", "w", encoding="utf-8") as f:
        for page in pages:
            f.write(f"URL: {page['url']}\n\n")
            f.write(f"Content:\n{page['content']}\n")
            f.write("-" * 80 + "\n\n")
