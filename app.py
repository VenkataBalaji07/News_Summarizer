import streamlit as st
import requests

# Set page config
st.set_page_config(page_title="News Summarization & TTS", page_icon="📰", layout="wide")

# Title of the application
st.markdown(
    """
    <h2 style='text-align: center; color: blue;'>News Summarization & Text-to-Speech Application</h2>
    """,
    unsafe_allow_html=True,
)

# Input field for company name
company = st.text_input("🔍 Enter a company name:", "")

# When the "Search News" button is clicked
if st.button("Search News"):
    if company:
        with st.spinner("Fetching news..."):
            try:
                response = requests.get(f"http://127.0.0.1:5000/get_news?company={company}")
                
                # Check if the response is successful
                if response.status_code == 200:
                    data = response.json()

                    # Sentiment Summary
                    st.subheader("📊 Sentiment Summary")
                    st.write(f"🟢 Positive: {data['sentiment_summary']['Positive']} | 🔴 Negative: {data['sentiment_summary']['Negative']} | ⚪ Neutral: {data['sentiment_summary']['Neutral']}")

                    # Display Latest News
                    st.subheader("📰 Latest News")
                    for article in data["articles"]:
                        sentiment_color = "🟢" if article["sentiment"] == "Positive" else "🔴" if article["sentiment"] == "Negative" else "⚪"
                        st.markdown(f"### {sentiment_color} [{article['title']}]({article['url']})")
                        st.write(article["summary"])

                    # Comparative Analysis
                    st.subheader("🔍 Comparative Analysis")
                    for comparison in data["comparative_analysis"]:
                        st.write(f"✅ {comparison['Comparison']}")

                    # Display Hindi TTS Audio
                    if data["tts_audio"]:
                        st.subheader("🎤 Hindi Audio Summary")
                        st.audio(f"http://127.0.0.1:5000/get_tts_audio?filename={data['tts_audio']}", format="audio/mp3")

                else:
                    st.error("⚠️ Error fetching news. Please try again.")
            except Exception as e:
                st.error(f"⚠️ Something went wrong: {e}")
    else:
        st.error("⚠️ Please enter a company name to search for news.")
