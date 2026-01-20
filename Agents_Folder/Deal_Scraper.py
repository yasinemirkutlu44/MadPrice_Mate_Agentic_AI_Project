from pydantic import BaseModel, Field
from typing import List, Dict, Self
from bs4 import BeautifulSoup
import re
import feedparser
from tqdm import tqdm
import requests
import time

feeds = [
    "https://www.dealnews.com/c142/Electronics/?rss=1",
    "https://www.dealnews.com/c39/Computers/?rss=1",
    "https://www.dealnews.com/f1912/Smart-Home/?rss=1",
    "https://www.dealnews.com/c238/Automotive/?rss=1",
    "https://www.dealnews.com/c196/Home-Garden/?rss=1",
]



# Imports:
# - Pydantic models (BaseModel/Field) for structured data validation
# - typing helpers (List, Dict, Self)
# - BeautifulSoup + regex for cleaning/extracting text from HTML
# - feedparser for reading RSS feeds
# - tqdm for optional progress bar
# - requests to fetch full deal pages
# - time to sleep between requests (polite scraping)

def extract(html_snippet: str) -> str:
    # Takes an HTML snippet (usually the RSS "summary") and tries to extract clean text.
    soup = BeautifulSoup(html_snippet, "html.parser")

    # Looks specifically for a <div class="snippet summary"> which contains the useful summary text
    snippet_div = soup.find("div", class_="snippet summary")

    if snippet_div:
        # Get the text content and strip whitespace
        description = snippet_div.get_text(strip=True)

        # Extra cleanup: parse again + remove any remaining HTML tags
        description = BeautifulSoup(description, "html.parser").get_text()
        description = re.sub("<[^<]+?>", "", description)

        result = description.strip()
    else:
        # Fallback: if that div isn't found, just return the raw snippet
        result = html_snippet

    # Replace newlines with spaces for a single-line summary
    return result.replace("\n", " ")


class ScrapedDeal:
    # Plain Python class representing a deal scraped from RSS + the deal page itself.
    # Fields: category/title/summary/url/details/features

    def __init__(self, entry: Dict[str, str]):
        # Build one ScrapedDeal from one RSS entry dict
        self.title = entry["title"]                       # RSS title
        self.summary = extract(entry["summary"])          # cleaned RSS summary text
        self.url = entry["links"][0]["href"]              # deal URL

        # Fetch the deal page HTML and parse it
        stuff = requests.get(self.url).content
        soup = BeautifulSoup(stuff, "html.parser")

        # Pull the main content section text from the page
        content = soup.find("div", class_="content-section").get_text()
        content = content.replace("\nmore", "").replace("\n", " ")

        # If the page contains a "Features" section, split it into details vs features
        if "Features" in content:
            self.details, self.features = content.split("Features", 1)
        else:
            self.details = content
            self.features = ""

        # Truncate long fields so later prompts/models don't get too much text
        self.truncate()

    def truncate(self):
        # Keep text fields at reasonable lengths (prompt-size control)
        self.title = self.title[:100]
        self.details = self.details[:500]
        self.features = self.features[:500]

    def __repr__(self):
        # What prints when you print the object
        return f"<{self.title}>"

    def describe(self):
        # Returns a formatted multi-line string (good for feeding into an LLM prompt)
        return (
            f"Title: {self.title}\n"
            f"Details: {self.details.strip()}\n"
            f"Features: {self.features.strip()}\n"
            f"URL: {self.url}"
        )

    @classmethod
    def fetch(cls, show_progress: bool = False) -> List[Self]:
        # Pull deals from all RSS feeds (first 10 entries per feed)
        deals = []
        feed_iter = tqdm(feeds) if show_progress else feeds  # optional progress bar

        for feed_url in feed_iter:
            feed = feedparser.parse(feed_url)               # parse RSS feed
            for entry in feed.entries[:10]:                 # take up to 10 items per feed
                deals.append(cls(entry))                    # create ScrapedDeal from entry
                time.sleep(0.05)                            # small delay to be polite
        return deals


class Deal(BaseModel):
    # Pydantic model: the "clean" structured representation you want an LLM to produce
    product_description: str = Field(
        description="A 3-4 sentence summary of the product itself (no discount talk)."
    )
    price: float = Field(
        description="The actual advertised price (after discounts)."
    )
    url: str = Field(
        description="Deal URL from the input."
    )


class DealSelection(BaseModel):
    # Pydantic model: a container requiring a list of 5 chosen deals
    deals: List[Deal] = Field(
        description="Pick 10 deals with the clearest price and best description."
    )


class Opportunity(BaseModel):
    # Pydantic model: represents a deal where your estimated true price is higher than the listed one
    deal: Deal          # the deal itself
    estimate: float     # your predicted fair price
    discount: float     # estimate - deal.price (how undervalued it is)
