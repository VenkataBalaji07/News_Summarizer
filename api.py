import requests
from flask import Flask, request, jsonify, send_file
from newspaper import Article
from bs4 import BeautifulSoup
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from gtts import gTTS
from deep_translator import GoogleTranslator
import os
import time
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
analyzer = SentimentIntensityAnalyzer()

def fetch_news_urls(company_name):
    """Fetch news article URLs from Bing News."""
    search_url = f"https://www.bing.com/news/search?q={company_name}+news"
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(search_url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    articles = []
    seen_urls = set()

    for item in soup.select("a"):
        link = item.get("href")
        if link and link.startswith("http") and "bing.com" not in link and "msn.com" not in link:
            if link not in seen_urls:
                articles.append(link)
                seen_urls.add(link)
        if len(articles) >= 10:
            break

    return articles

def analyze_sentiment(text):
    """Perform sentiment analysis using VADER."""
    score = analyzer.polarity_scores(text)["compound"]
    if score > 0.05:
        return "Positive"
    elif score < -0.05:
        return "Negative"
    else:
        return "Neutral"

def extract_article_details(url, company_name):
    """Extracts title, summary, and sentiment from a news URL."""
    try:
        article = Article(url)
        article.download()
        article.parse()
        article.nlp()

        title = article.title if article.title else "No Title Found"
        summary = article.summary if article.summary else "Summary not available"

        if company_name.lower() not in title.lower():
            return None  

        sentiment = analyze_sentiment(summary)

        return {
            "title": title,
            "summary": summary,
            "sentiment": sentiment,
            "url": url
        }
    except Exception:
        return None

def generate_hindi_speech(text):
    """Convert summarized text to Hindi speech."""
    try:
        translated_text = GoogleTranslator(source='en', target='hi').translate(text)
        tts = gTTS(text=translated_text, lang="hi")
        audio_file = f"output_{int(time.time())}.mp3"
        tts.save(audio_file)
        return audio_file
    except Exception as e:
        print(f"Error generating speech: {e}")
        return None

@app.route('/get_news', methods=['GET'])
def get_news():
    company = request.args.get("company")
    if not company:
        return jsonify({"error": "Company name is required"}), 400

    news_urls = fetch_news_urls(company)
    if not news_urls:
        return jsonify({"error": "No valid news articles found."}), 404

    articles = []
    seen_titles = set()
    sentiment_counts = {"Positive": 0, "Negative": 0, "Neutral": 0}

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(lambda url: extract_article_details(url, company), news_urls)

    for article in results:
        if article and article["title"] not in seen_titles:
            articles.append(article)
            seen_titles.add(article["title"])
            sentiment_counts[article["sentiment"]] += 1

    if not articles:
        return jsonify({"error": "No relevant articles found"}), 404

    # Comparative Analysis
    comparative_analysis = []
    for i in range(len(articles) - 1):
        comparative_analysis.append({
            "Comparison": f"Article {i+1} discusses '{articles[i]['title']}' while Article {i+2} covers '{articles[i+1]['title']}'."
        })

    # Generate Hindi TTS
    summary_text = " ".join([article["summary"] for article in articles[:5]])
    hindi_audio = generate_hindi_speech(summary_text)

    return jsonify({
        "articles": articles,
        "comparative_analysis": comparative_analysis,
        "sentiment_summary": sentiment_counts,
        "tts_audio": hindi_audio
    })

@app.route('/get_tts_audio', methods=['GET'])
def get_tts_audio():
    filename = request.args.get("filename")
    if not filename or not os.path.exists(filename):
        return jsonify({"error": "Audio file not found"}), 404
    return send_file(filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
