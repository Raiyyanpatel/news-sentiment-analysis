import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration settings for the news sentiment analysis application"""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    # API Keys
    NEWSAPI_KEY = os.environ.get('NEWSAPI_KEY', '')
    
    # Database settings
    DATABASE_PATH = os.path.join('data', 'sentiment_analysis.db')
    
    # News fetching settings
    DEFAULT_NEWS_SOURCES = [
        'bbc-news', 'cnn', 'reuters', 'associated-press', 
        'the-guardian-uk', 'abc-news', 'cbs-news'
    ]
    
    RSS_FEEDS = [
        'http://feeds.bbci.co.uk/news/rss.xml',
        'http://rss.cnn.com/rss/edition.rss',
        'https://feeds.reuters.com/reuters/topNews',
        'https://www.theguardian.com/uk/rss'
    ]
    
    # Sentiment analysis settings
    SENTIMENT_MODEL = 'cardiffnlp/twitter-roberta-base-sentiment-latest'
    CONFIDENCE_THRESHOLD = 0.6
    
    # Caching settings
    CACHE_TIMEOUT = 3600  # 1 hour in seconds
    
    # Rate limiting
    REQUESTS_PER_MINUTE = 100
    
    @staticmethod
    def validate_config():
        """Validate that required configuration is present"""
        warnings = []
        
        if not Config.NEWSAPI_KEY:
            warnings.append("NEWSAPI_KEY not set - NewsAPI features will be limited")
        
        return warnings