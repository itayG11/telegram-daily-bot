import os
import feedparser
import requests
from anthropic import Anthropic

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

RSS_SOURCES = {
    "Global Economy & Markets": "https://www.cnbc.com/id/10001147/device/rss/rss.html",
    "World Politics": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "Crypto": "https://cointelegraph.com/rss",
    "Artificial Intelligence": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "Technology": "https://techcrunch.com/feed/",
    "Israel News": "https://www.timesofisrael.com/feed/",
}

MAX_HEADLINES_PER_TOPIC = 15
TELEGRAM_MESSAGE_LIMIT = 4000


def fetch_headlines(url: str) -> list[str]:
    feed = feedparser.parse(url)
    return [entry.title for entry in feed.entries[:MAX_HEADLINES_PER_TOPIC]]


def build_raw_news_text() -> str:
    sections = []
    for topic, url in RSS_SOURCES.items():
        headlines = fetch_headlines(url)
        headlines_text = "\n".join(f"- {title}" for title in headlines)
        sections.append(f"### {topic}\n{headlines_text}")
    return "\n\n".join(sections)


def summarize_with_claude(raw_news_text: str) -> str:
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = (
        "Below are raw news headlines from 6 different topics, each topic marked with ###. "
        "Write the summary in English. For each topic, write 3-4 substantive paragraphs "
        "explaining background, context, and implications. "
        "Use the topic name as a heading (without the ### symbol). Leave a blank line between "
        "topics. Do not add an intro or a closing summary. For each topic, focus specifically "
        "on the following, and ignore everything else:\n\n"
        "### Global Economy & Markets\n"
        "Focus on: major index moves (S&P, Nasdaq), central bank interest rate decisions, "
        "inflation/employment data, earnings reports from major companies. "
        "Ignore: minor daily fluctuations that aren't significant long-term.\n\n"
        "### World Politics\n"
        "Focus on: major government decisions, elections/referendums, international relations "
        "(agreements/sanctions), significant geopolitical conflicts. "
        "Ignore: minor political statements that don't lead to concrete action.\n\n"
        "### Crypto\n"
        "Focus on: regulation (government approvals/bans), major price moves (not routine "
        "volatility), institutional partnerships (banks/major companies entering the space), "
        "significant protocol upgrades, large-scale security breaches or hacks. "
        "Ignore: minor influencer drama or routine price chatter.\n\n"
        "### Artificial Intelligence\n"
        "Focus on: new model releases, major regulatory moves, significant mergers/"
        "acquisitions, research breakthroughs with practical implications. "
        "Ignore: another startup raising a funding round unless the amount or name is "
        "genuinely significant.\n\n"
        "### Technology\n"
        "Focus on: major product launches from leading companies (Apple, Google, Meta, etc.), "
        "acquisitions/mergers, significant platform policy changes. "
        "Ignore: minor software updates or small app features.\n\n"
        "### Israel News\n"
        "Focus on: security (military actions, threats, security decisions), government "
        "policy, local economy (Bank of Israel, the shekel, unemployment). "
        "Ignore: lifestyle or human-interest pieces.\n\n"
        "Now here are the raw headlines to summarize:\n\n"
        f"{raw_news_text}"
    )
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=10000,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def send_telegram_message(text: str) -> None:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    response = requests.post(url, data=payload)
    response.raise_for_status()


def send_long_message_in_chunks(text: str) -> None:
    paragraphs = text.split("\n\n")
    current_chunk = ""
    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) + 2 > TELEGRAM_MESSAGE_LIMIT:
            send_telegram_message(current_chunk)
            current_chunk = paragraph
        else:
            current_chunk = f"{current_chunk}\n\n{paragraph}" if current_chunk else paragraph
    if current_chunk:
        send_telegram_message(current_chunk)


if __name__ == "__main__":
    raw_news = build_raw_news_text()
    summary = summarize_with_claude(raw_news)
    send_long_message_in_chunks(summary)