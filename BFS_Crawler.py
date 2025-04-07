import requests  # For making HTTP GET requests
import json  # For saving data as JSON
import csv  # For saving data as CSV
import time  # For adding delays (sleep) between requests
import re  # For regular expressions
from collections import deque  # For queue-based (BFS-like) crawling
from urllib.parse import urljoin, urlparse  # For handling relative/absolute URLs and parsing
from bs4 import BeautifulSoup  # For parsing HTML

# ---------------------------------------------------------------------
# Configuration Parameters
# ---------------------------------------------------------------------
MAX_DEPTH = 3  # Maximum link depth from the start URL
MAX_PAGES = 500  # Maximum total pages to visit
SLEEP_BETWEEN_REQUESTS = 0.5  # Delay (seconds) between requests (politeness)
ACCEPTED_PATH_REGEX = re.compile(r"(blog|article|post|category|archive|news)", re.IGNORECASE)
TIMEOUT_SECS = 8  # Timeout (seconds) for each request


# ---------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------

def clean_text(text):
    """
    Trims leading/trailing whitespace and replaces multiple consecutive
    whitespace characters (including newlines, tabs) with a single space.
    """
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def extract_date_info(text):
    """
    Given a string containing a date (with words like 'Posted', 'Published' or 'Updated'),
    removes the literal descriptors and returns the date string.
    For example:
      "Posted on Apr 3, 2025" becomes "Apr 3, 2025"
      "Published Apr 3, 2025 6:01 PM EDT" becomes "Apr 3, 2025 6:01 PM EDT"
    """
    text = clean_text(text)
    # Remove leading keywords and optional "on"
    date = re.sub(r"^(Posted|Published|Updated)\s+(on\s+)?", "", text, flags=re.IGNORECASE)
    return date.strip()


def get_article_details(article_url):
    """
    Fetches the full article page and extracts:
      - Full article text (from a dedicated content container or all <p> tags)
      - The published date (from a timestamp element)
      - Author(s) (by selecting author link(s) from the byline)

    Returns a dictionary with keys: "Full Article", "Date Posted", "Author(s)".
    """
    details = {"Full Article": "", "Date Posted": "", "Author(s)": []}
    try:
        r = requests.get(article_url, timeout=TIMEOUT_SECS)
        if r.status_code != 200:
            print(f"Could not retrieve article content at {article_url} (status={r.status_code})")
            return details

        soup = BeautifulSoup(r.text, "html.parser")

        # ---------------------------
        # Extract Full Article Text
        # ---------------------------
        article_container = soup.find("div", class_="entry-content")
        if article_container:
            paragraphs = article_container.find_all("p")
            full_text = " ".join(clean_text(p.get_text(separator=" ")) for p in paragraphs)
        else:
            # Fallback: use all <p> tags
            paragraphs = soup.find_all("p")
            full_text = " ".join(clean_text(p.get_text(separator=" ")) for p in paragraphs)
        details["Full Article"] = full_text

        # ---------------------------
        # Extract Published Date
        # ---------------------------
        date_tag = soup.find(class_=lambda c: c and "byline-item-timestamp" in c)
        if date_tag:
            date_text = clean_text(date_tag.get_text())
            details["Date Posted"] = extract_date_info(date_text)
        elif soup.find("p", class_=lambda c: c and "card-post-date" in c):
            date_text = clean_text(soup.find("p", class_=lambda c: c and "card-post-date" in c).get_text())
            details["Date Posted"] = extract_date_info(date_text)

        # ---------------------------
        # Extract Author(s)
        # ---------------------------
        author_tags = soup.select(".byline-item-author a")
        if not author_tags:
            author_tags = soup.select(".article-byline a")
        authors = []
        for tag in author_tags:
            name = clean_text(tag.get_text())
            if name:
                authors.append(name)
        details["Author(s)"] = authors

    except requests.exceptions.RequestException as e:
        print(f"Request error retrieving {article_url}: {e}")
    except Exception as e:
        print(f"Error parsing {article_url}: {e}")

    return details


def extract_articles_from_page(page_url):
    """
    Visits a page presumed to contain article preview cards,
    extracts metadata (title, date, author, etc.) and the full article text
    from linked detail pages.

    Returns a list of dictionaries, where each dictionary represents an article.
    """
    articles = []
    try:
        resp = requests.get(page_url, timeout=TIMEOUT_SECS)
        if resp.status_code != 200:
            print(f"Failed to retrieve page: {page_url} (status={resp.status_code})")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        article_cards = soup.find_all("div", class_="card-post")

        for card in article_cards:
            # (1) Extract the article link
            link_tag = card.find("a", class_="card-post-title-link")
            if not link_tag:
                link_tag = card.find("a", class_="card-post-image-link")
            if not link_tag:
                continue
            article_url = link_tag.get("href", "").strip()
            if not article_url:
                continue

            # (2) Extract the article title
            title_tag = link_tag.find("h3", class_="card-post-title")
            if not title_tag:
                title_tag = card.find("h3", class_="card-post-title")
            article_title = clean_text(title_tag.get_text()) if title_tag else ""

            # (3) Extract the article sections/categories
            section_list = []
            cat_badge_tags = card.select(".post-tax-badges .cat-name-badge")
            if not cat_badge_tags:
                cat_badge_tags = card.find_all("a", class_="cat-name-badge")
            for ctag in cat_badge_tags:
                section_list.append(clean_text(ctag.get_text()))
            section_str = ", ".join(section_list)

            # (4) Extract date posted from the preview card
            date_posted = ""
            date_tag = card.find("p", class_=lambda c: c and "card-post-date" in c)
            if date_tag:
                date_posted = extract_date_info(clean_text(date_tag.get_text()))

            # (5) Extract article author(s) from the preview card
            authors = []
            author_tags = card.select(".card-post-byline a")
            for atag in author_tags:
                name = clean_text(atag.get_text())
                if name:
                    authors.append(name)

            # (6) Extract any short "updates" snippet from the card
            updates = ""
            updates_tag = card.find("p", class_="card-post-dek")
            if updates_tag:
                updates = clean_text(updates_tag.get_text())

            # (7) Retrieve full article details from the article page
            details = get_article_details(article_url)
            if not date_posted and details.get("Date Posted"):
                date_posted = details["Date Posted"]
            if not authors and details.get("Author(s)"):
                authors = details["Author(s)"]
            full_text = details.get("Full Article", "")

            article_data = {
                "Section": section_str,
                "Title": article_title,
                "Link": article_url,
                "Author(s)": authors,
                "Date Posted": date_posted,
                "Date Updated": "",
                "Updates": updates,
                "Full Article": full_text,
            }
            articles.append(article_data)

        return articles

    except requests.exceptions.RequestException as e:
        print(f"Request error retrieving {page_url}: {e}")
        return []
    except Exception as e:
        print(f"Error extracting articles from page {page_url}: {e}")
        return []


def crawl_website(start_url="https://www.twz.com/"):
    """
    Core crawler function. Performs a breadth-first traversal (BFS) of links
    on the same domain as 'start_url'. Only follows links whose paths match
    ACCEPTED_PATH_REGEX, and respects the global limits: MAX_DEPTH and MAX_PAGES.

    Prevents duplicate article retrieval by keeping a set of scraped article URLs.

    Returns a list of all extracted articles from visited pages.
    """
    domain = urlparse(start_url).netloc
    visited = set()
    scraped_article_urls = set()
    queue = deque([(start_url, 0)])
    all_articles = []
    pages_visited = 0

    while queue:
        current_url, depth = queue.popleft()

        if current_url in visited:
            continue

        visited.add(current_url)

        if depth > MAX_DEPTH or pages_visited >= MAX_PAGES:
            continue

        print(f"Crawling URL (depth {depth}): {current_url}")

        articles_on_page = extract_articles_from_page(current_url)
        for article in articles_on_page:
            # Check if this article's URL has been processed before
            if article["Link"] not in scraped_article_urls:
                scraped_article_urls.add(article["Link"])
                all_articles.append(article)

        pages_visited += 1

        if depth < MAX_DEPTH and pages_visited < MAX_PAGES:
            try:
                resp = requests.get(current_url, timeout=TIMEOUT_SECS)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for a_tag in soup.find_all("a", href=True):
                        href = a_tag["href"].strip()
                        if not href:
                            continue

                        new_url = urljoin(current_url, href)
                        parsed_new = urlparse(new_url)

                        if (parsed_new.netloc == domain and
                                parsed_new.scheme in ("http", "https") and
                                new_url not in visited):
                            if ACCEPTED_PATH_REGEX.search(parsed_new.path):
                                queue.append((new_url, depth + 1))
            except requests.exceptions.RequestException as e:
                print(f"Request error crawling page {current_url}: {e}")
                continue

        time.sleep(SLEEP_BETWEEN_REQUESTS)

    return all_articles


# ---------------------------------------------------------------------
# Main Routine
# ---------------------------------------------------------------------
if __name__ == "__main__":
    print("Crawling the twz.com domain for articles...")

    articles_data = crawl_website("https://www.twz.com/")
    print(f"Found {len(articles_data)} total unique articles within constraints.")

    # Save extracted data to a JSON file
    json_filename = "twz_articles_fullsite_limited2.json"
    try:
        with open(json_filename, "w", encoding="utf-8") as jf:
            json.dump(articles_data, jf, indent=2, ensure_ascii=False)
        print(f"Article data saved to '{json_filename}'.")
    except Exception as e:
        print(f"Error saving JSON: {e}")

    # Save extracted data to a CSV file
    csv_filename = "twz_articles_fullsite_limited2.csv"
    fieldnames = [
        "Section",
        "Title",
        "Full Article",
        "Author(s)",
        "Date Posted",
        "Date Updated",
        "Updates",
        "Link",
    ]
    try:
        with open(csv_filename, "w", encoding="utf-8", newline="") as cf:
            writer = csv.DictWriter(cf, fieldnames=fieldnames)
            writer.writeheader()
            for article in articles_data:
                authors_str = "; ".join(article["Author(s)"]) if article["Author(s)"] else ""
                row = {
                    "Section": article["Section"],
                    "Title": article["Title"],
                    "Full Article": article["Full Article"],
                    "Author(s)": authors_str,
                    "Date Posted": article["Date Posted"],
                    "Date Updated": article["Date Updated"],
                    "Updates": article["Updates"],
                    "Link": article["Link"],
                }
                writer.writerow(row)
        print(f"Article data saved to '{csv_filename}'.")
    except Exception as e:
        print(f"Error saving CSV: {e}")
