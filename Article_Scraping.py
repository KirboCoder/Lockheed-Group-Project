"""
Scrape the blog website https://www.twz.com/ to extract each article's:
    1) Section(s)
    2) Title
    3) Full Article Text
    4) Author(s)
    5) Date Posted
    6) Date Updated
    7) Updates (if present)
    8) Link to Article

Data is stored in JSON and CSV formats for easy ingestion into a real-time article display dashboard (e.g., Tableau) & possible AI chatbot.
"""

import requests
import json
import csv
import time
import re
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------
def clean_text(text):
    """
    Clean text by stripping unwanted whitespace and newlines.
    """
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def extract_date_info(date_string):
    """
    Attempt to parse 'Posted on...' or 'Updated on...' text to separate
    posted and updated dates. Returns (date_posted, date_updated).
    Accepts partial/relative times (e.g. 'Posted Yesterday') as text.
    """
    date_string = clean_text(date_string)
    posted_pattern = r"Posted\s+(on\s+.*|\w+)$"
    updated_pattern = r"Updated\s+(on\s+.*|\w+)$"

    date_posted = None
    date_updated = None

    match_posted = re.search(posted_pattern, date_string, re.IGNORECASE)
    if match_posted:
        # remove "on " if present
        date_posted = match_posted.group(1).replace("on ", "").strip()

    match_updated = re.search(updated_pattern, date_string, re.IGNORECASE)
    if match_updated:
        date_updated = match_updated.group(1).replace("on ", "").strip()

    return (date_posted, date_updated)


def get_full_article_text(article_url):
    """
    Requests the article detail page and attempts to extract the main
    article text. We look for a <div class="entry-content"> by default,
    but fall back to all <p> tags if needed.
    """
    try:
        r = requests.get(article_url, timeout=10)
        if r.status_code != 200:
            print(f"Could not retrieve article content at {article_url} (status={r.status_code})")
            return ""

        soup = BeautifulSoup(r.text, "html.parser")

        # Attempt to find main article container
        article_container = soup.find("div", class_="entry-content")

        if article_container:
            paragraphs = article_container.find_all("p")
            full_text = " ".join(clean_text(p.get_text(separator=" ")) for p in paragraphs)
        else:
            # Fallback: gather all paragraphs if no "entry-content" is found
            all_paras = soup.find_all("p")
            full_text = " ".join(clean_text(p.get_text(separator=" ")) for p in all_paras)

        return full_text

    except Exception as e:
        print(f"Error retrieving full article text from {article_url}: {e}")
        return ""


# ---------------------------------------------------------------------
# Main scraper function
# ---------------------------------------------------------------------
def scrape_homepage_articles(homepage_url="https://www.twz.com/"):
    """
    Scrape the homepage to identify articles. Extract:
        - Section/Category
        - Title
        - Link to the article (preferring <a class="card-post-title-link">)
        - Author(s)
        - Dates (posted/updated)
        - "Updates" (short snippet or 'dek' text)
        - Full article text (by visiting detail page)
    """
    all_articles = []
    try:
        resp = requests.get(homepage_url, timeout=10)
        if resp.status_code != 200:
            print(f"Failed to retrieve homepage with status code {resp.status_code}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        # The homepage has multiple "card-post" elements for articles
        article_cards = soup.find_all("div", class_="card-post")

        for card in article_cards:
            # 1) Try the correct link first: <a class="card-post-title-link">
            link_tag = card.find("a", class_="card-post-title-link")
            # Fallback: in case that class changes or is absent
            if not link_tag:
                link_tag = card.find("a", class_="card-post-image-link")
            if not link_tag:
                continue

            article_url = link_tag.get("href", "").strip()
            if not article_url:
                continue

            # 2) Extract the Title
            # The same container often has <h3 class="card-post-title">...
            title_tag = link_tag.find("h3", class_="card-post-title")
            # or fallback:
            if not title_tag:
                # maybe directly in link
                title_tag = card.find("h3", class_="card-post-title")
            article_title = clean_text(title_tag.get_text()) if title_tag else ""

            # 3) Extract the Section(s)
            section_list = []
            cat_badge_tags = card.select(".post-tax-badges .cat-name-badge")
            if not cat_badge_tags:
                # fallback: some pages might have direct .cat-name-badge anchors
                cat_badge_tags = card.find_all("a", class_="cat-name-badge")
            for ctag in cat_badge_tags:
                section_list.append(clean_text(ctag.get_text()))
            section_str = ", ".join(section_list)

            # 4) Extract date posted/updated
            date_posted, date_updated = (None, None)
            byline_items = card.select(".card-post-inline-meta .inline-meta-item")
            for item in byline_items:
                text_item = clean_text(item.get_text())
                if ("Posted" in text_item or "Updated" in text_item) and len(text_item) < 60:
                    p_date, u_date = extract_date_info(text_item)
                    if p_date:
                        date_posted = p_date
                    if u_date:
                        date_updated = u_date

            # 5) Extract Authors
            # Usually inside .card-post-byline span.byline-text
            authors = []
            byline_author_tags = card.select(".card-post-byline span.byline-text")
            if byline_author_tags:
                for btag in byline_author_tags:
                    authors_text = clean_text(btag.get_text())
                    authors_text = authors_text.replace("By ", "")
                    splitted = re.split(r"[,&]|\band\b", authors_text)
                    splitted_cleaned = [clean_text(x) for x in splitted if x.strip()]
                    authors.extend(splitted_cleaned)
            else:
                # Fallback: look for .card-post-byline
                alt_byline = card.select_one(".card-post-byline")
                if alt_byline:
                    btext = clean_text(alt_byline.get_text())
                    if btext.lower().startswith("by "):
                        btext = btext[3:].strip()
                    splitted = re.split(r"[,&]|\band\b", btext)
                    splitted_cleaned = [clean_text(x) for x in splitted if x.strip()]
                    authors.extend(splitted_cleaned)

            # 6) Snippet text as "Updates" placeholder
            updates = ""
            updates_tag = card.find("p", class_="card-post-dek")
            if updates_tag:
                updates = clean_text(updates_tag.get_text())

            # 7) Get the full article text from the detail page
            full_text = get_full_article_text(article_url)

            # 8) Build dictionary record
            article_data = {
                "Section": section_str,
                "Title": article_title,
                "Link": article_url,
                "Author(s)": authors,
                "Date Posted": date_posted or "",
                "Date Updated": date_updated or "",
                "Updates": updates,
                "Full Article": full_text,
            }
            all_articles.append(article_data)

        return all_articles

    except Exception as exc:
        print(f"Error scraping homepage: {exc}")
        return []


# ---------------------------------------------------------------------
# Main routine
# ---------------------------------------------------------------------
if __name__ == "__main__":
    print("Scraping the blog homepage for articles...")
    articles_data = scrape_homepage_articles("https://www.twz.com/")
    print(f"Found {len(articles_data)} articles on the homepage.")

    # Save to JSON
    json_filename = "twz_articles.json"
    with open(json_filename, "w", encoding="utf-8") as jf:
        json.dump(articles_data, jf, indent=2, ensure_ascii=False)
    print(f"Article data saved to '{json_filename}'.")

    # Save to CSV
    csv_filename = "twz_articles.csv"
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
    with open(csv_filename, "w", encoding="utf-8", newline="") as cf:
        writer = csv.DictWriter(cf, fieldnames=fieldnames)
        writer.writeheader()
        for article in articles_data:
            # For CSV, join authors in a single string
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
