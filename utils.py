import requests
from newspaper import Article
from bs4 import BeautifulSoup
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import time
import os
from concurrent.futures import ThreadPoolExecutor
from gtts import gTTS
from deep_translator import GoogleTranslator

# Initialize Sentiment Analyzer
analyzer = SentimentIntensityAnalyzer()

def get_news_urls(company_name):
    """Fetch 10 unique news article URLs from Bing News"""
    search_url = f"https://www.bing.com/news/search?q={company_name}&count=20"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(search_url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")

        articles = []
        seen_urls = set()

        for item in soup.find_all("a", href=True):
            link = item["href"]
            if link.startswith("http") and "bing.com" not in link and "msn.com" not in link:
                if link not in seen_urls:
                    articles.append(link)
                    seen_urls.add(link)

            if len(articles) >= 10:
                break

        if len(articles) < 10:
            print(f"⚠️ Only {len(articles)} articles found. Try a different company name.")

        return articles
    except Exception as e:
        print(f"⚠️ Error fetching news: {str(e)}")
        return []

def analyze_sentiment(text):
    """Perform sentiment analysis on individual sentences"""
    positive_count, negative_count, neutral_count = 0, 0, 0
    sentences = text.split(". ")

    for sentence in sentences:
        sentiment_score = analyzer.polarity_scores(sentence)["compound"]
        if sentiment_score > 0.05:
            positive_count += 1
        elif sentiment_score < -0.05:
            negative_count += 1
        else:
            neutral_count += 1

    overall_sentiment = (
        "Positive" if positive_count > negative_count
        else "Negative" if negative_count > positive_count
        else "Neutral"
    )

    return overall_sentiment, positive_count, negative_count, neutral_count

def extract_article_details(url, company_name):
    """Extract title, summary, and sentence-level sentiment from a news URL"""
    try:
        article = Article(url)
        article.download()
        time.sleep(2)
        article.parse()

        if not article.text or len(article.text) < 500:
            return None

        article.nlp()
        title = article.title if article.title else "No Title Found"
        summary = " ".join(article.summary.split(". ")[:3]) + "."

        if company_name.lower() not in title.lower() and company_name.lower() not in summary.lower():
            return None  

        sentiment, pos_count, neg_count, neu_count = analyze_sentiment(summary)

        return {
            "title": title,
            "summary": summary,
            "sentiment": sentiment,
            "positive_sentences": pos_count,
            "negative_sentences": neg_count,
            "neutral_sentences": neu_count,
            "url": url
        }
    except Exception as e:
        return {"error": f"Failed to extract article from {url} - {str(e)}"}

def generate_hindi_speech(text, pos, neg, neu, sentiment_counts):
    """Translate summary to Hindi and convert to speech (Fixes character limit issue)"""
    try:
        sentiment_summary = (
            f"सकारात्मक समाचार: {sentiment_counts['Positive']}, "
            f"नकारात्मक समाचार: {sentiment_counts['Negative']}, "
            f"तटस्थ समाचार: {sentiment_counts['Neutral']}. "
        )

        # Ensure text does not exceed 5000 characters
        max_length = 5000 - len(sentiment_summary)  # Leave space for sentiment summary
        text = text[:max_length]  # Truncate text if too long

        translated_text = GoogleTranslator(source="en", target="hi").translate(text)
        tts_text = sentiment_summary + translated_text  # Combine sentiment summary + translated news

        tts = gTTS(text=tts_text, lang="hi")
        tts.save("news_summary_hindi.mp3")
        print("✅ Hindi TTS generated successfully! 🔊")
    except Exception as e:
        print(f"⚠️ Failed to generate Hindi speech: {str(e)}")

if __name__ == "__main__":
    company = input("Enter company name: ")
    news_urls = get_news_urls(company)
    
    if not news_urls:
        print("⚠️ No valid news articles found.")
    else:
        articles = []
        seen_titles = set()
        total_pos, total_neg, total_neu = 0, 0, 0
        sentiment_counts = {"Positive": 0, "Negative": 0, "Neutral": 0}

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = executor.map(lambda url: extract_article_details(url, company), news_urls)

        for article_data in results:
            if article_data and "error" not in article_data and article_data["title"] not in seen_titles:
                articles.append(article_data)
                seen_titles.add(article_data["title"])

                # Sum up sentence counts
                total_pos += article_data["positive_sentences"]
                total_neg += article_data["negative_sentences"]
                total_neu += article_data["neutral_sentences"]

                # Count article-level sentiments
                sentiment_counts[article_data["sentiment"]] += 1

        end_time = time.time()
        print(f"✅ News extraction completed in {end_time - start_time:.2f} seconds")

        # Print extracted articles
        for idx, article in enumerate(articles, 1):
            print(f"{idx}. {article['title']} - {article['summary']} (Sentiment: {article['sentiment']})")
            print(f"   ➤ Positive Sentences: {article['positive_sentences']}, Negative: {article['negative_sentences']}, Neutral: {article['neutral_sentences']}\n")

        # 📊 Comparative Sentiment Analysis
        print("\n### 📊 Comparative Sentiment Analysis ###")
        print(f"🟢 Positive News: {sentiment_counts['Positive']}")
        print(f"🔴 Negative News: {sentiment_counts['Negative']}")
        print(f"⚪ Neutral News: {sentiment_counts['Neutral']}")

        # Generate Hindi Speech with sentiment breakdown
        if articles:
            full_summary = " ".join([article["summary"] for article in articles])
            full_summary = ". ".join(full_summary.split(". ")[:5]) + "."  # Limit to 5 sentences
            generate_hindi_speech(full_summary, total_pos, total_neg, total_neu, sentiment_counts)
