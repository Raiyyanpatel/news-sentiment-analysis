from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import os
from src.news_fetcher import NewsFetcher
from src.sentiment_analyzer import SentimentAnalyzer
from src.data_manager import DataManager
from src.visualizer import create_sentiment_chart, create_trend_chart
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Initialize components
news_fetcher = NewsFetcher()
sentiment_analyzer = SentimentAnalyzer()
data_manager = DataManager()

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_news():
    """Analyze news sentiment for given keywords"""
    try:
        data = request.get_json()
        keywords = data.get('keywords', '')
        sources = data.get('sources', ['newsapi'])
        limit = data.get('limit', 10)
        
        if not keywords:
            return jsonify({'error': 'Keywords are required'}), 400
        
        # Fetch news articles
        logger.info(f"Fetching news for keywords: {keywords}")
        articles = news_fetcher.fetch_news(keywords, sources, limit)
        
        if not articles:
            return jsonify({'error': 'No articles found'}), 404
        
        # Analyze sentiment
        logger.info(f"Analyzing sentiment for {len(articles)} articles")
        analyzed_articles = []
        
        for article in articles:
            sentiment_result = sentiment_analyzer.analyze(article['content'])
            article.update(sentiment_result)
            analyzed_articles.append(article)
        
        # Store results
        data_manager.store_analysis(keywords, analyzed_articles)
        
        return jsonify({
            'success': True,
            'articles': analyzed_articles,
            'summary': {
                'total_articles': len(analyzed_articles),
                'positive': len([a for a in analyzed_articles if a['sentiment'] == 'positive']),
                'negative': len([a for a in analyzed_articles if a['sentiment'] == 'negative']),
                'neutral': len([a for a in analyzed_articles if a['sentiment'] == 'neutral'])
            }
        })
        
    except Exception as e:
        logger.error(f"Error in analyze_news: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/history')
def get_history():
    """Get analysis history"""
    try:
        days = request.args.get('days', 7, type=int)
        history = data_manager.get_history(days)
        return jsonify(history)
    except Exception as e:
        logger.error(f"Error in get_history: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/trends/<keyword>')
def get_trends(keyword):
    """Get sentiment trends for a specific keyword"""
    try:
        days = request.args.get('days', 7, type=int)
        trends = data_manager.get_trends(keyword, days)
        return jsonify(trends)
    except Exception as e:
        logger.error(f"Error in get_trends: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chart/sentiment/<keyword>')
def sentiment_chart(keyword):
    """Generate sentiment distribution chart"""
    try:
        days = request.args.get('days', 7, type=int)
        chart_data = create_sentiment_chart(keyword, days)
        return jsonify(chart_data)
    except Exception as e:
        logger.error(f"Error in sentiment_chart: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chart/trends/<keyword>')
def trend_chart(keyword):
    """Generate sentiment trend chart"""
    try:
        days = request.args.get('days', 7, type=int)
        chart_data = create_trend_chart(keyword, days)
        return jsonify(chart_data)
    except Exception as e:
        logger.error(f"Error in trend_chart: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)
    
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)