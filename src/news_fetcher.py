import requests
import feedparser
from newsapi import NewsApiClient
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
import time
import re
from typing import List, Dict, Optional
from config import Config

logger = logging.getLogger(__name__)

class NewsFetcher:
    """Fetches news articles from multiple sources"""
    
    def __init__(self):
        self.newsapi_client = None
        if Config.NEWSAPI_KEY:
            self.newsapi_client = NewsApiClient(api_key=Config.NEWSAPI_KEY)
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def fetch_news(self, keywords: str, sources: List[str] = None, limit: int = 10) -> List[Dict]:
        """
        Fetch news articles from specified sources
        
        Args:
            keywords: Search keywords
            sources: List of source types ('newsapi', 'rss', 'web')
            limit: Maximum number of articles to fetch
        
        Returns:
            List of article dictionaries
        """
        if sources is None:
            sources = ['newsapi', 'rss']
        
        all_articles = []
        articles_per_source = max(1, limit // len(sources))
        
        for source in sources:
            try:
                if source == 'newsapi' and self.newsapi_client:
                    articles = self._fetch_from_newsapi(keywords, articles_per_source)
                elif source == 'rss':
                    articles = self._fetch_from_rss(keywords, articles_per_source)
                elif source == 'web':
                    articles = self._fetch_from_web(keywords, articles_per_source)
                else:
                    logger.warning(f"Unknown source: {source}")
                    continue
                
                all_articles.extend(articles)
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Error fetching from {source}: {str(e)}")
                continue
        
        # Remove duplicates and limit results
        unique_articles = self._remove_duplicates(all_articles)
        return unique_articles[:limit]
    
    def _fetch_from_newsapi(self, keywords: str, limit: int) -> List[Dict]:
        """Fetch articles from NewsAPI"""
        try:
            # Search for articles
            response = self.newsapi_client.get_everything(
                q=keywords,
                language='en',
                sort_by='relevancy',
                page_size=min(limit, 20),
                sources=','.join(Config.DEFAULT_NEWS_SOURCES[:5])  # Limit sources
            )
            
            articles = []
            for article in response.get('articles', []):
                if article.get('content') and len(article['content']) > 100:
                    processed_article = {
                        'title': article.get('title', ''),
                        'content': self._clean_content(article.get('content', '')),
                        'description': article.get('description', ''),
                        'url': article.get('url', ''),
                        'source': article.get('source', {}).get('name', 'NewsAPI'),
                        'published_at': self._parse_date(article.get('publishedAt')),
                        'author': article.get('author', 'Unknown')
                    }
                    articles.append(processed_article)
            
            logger.info(f"Fetched {len(articles)} articles from NewsAPI")
            return articles
            
        except Exception as e:
            logger.error(f"NewsAPI error: {str(e)}")
            return []
    
    def _fetch_from_rss(self, keywords: str, limit: int) -> List[Dict]:
        """Fetch articles from RSS feeds"""
        articles = []
        keywords_lower = keywords.lower()
        
        for feed_url in Config.RSS_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries:
                    # Check if keywords match title or summary
                    title = entry.get('title', '').lower()
                    summary = entry.get('summary', '').lower()
                    
                    if keywords_lower in title or keywords_lower in summary:
                        content = self._extract_full_content(entry.get('link', ''))
                        if content and len(content) > 100:
                            article = {
                                'title': entry.get('title', ''),
                                'content': content,
                                'description': entry.get('summary', ''),
                                'url': entry.get('link', ''),
                                'source': feed.feed.get('title', 'RSS Feed'),
                                'published_at': self._parse_date(entry.get('published')),
                                'author': entry.get('author', 'Unknown')
                            }
                            articles.append(article)
                            
                            if len(articles) >= limit:
                                break
                
                if len(articles) >= limit:
                    break
                    
            except Exception as e:
                logger.error(f"RSS feed error for {feed_url}: {str(e)}")
                continue
        
        logger.info(f"Fetched {len(articles)} articles from RSS feeds")
        return articles
    
    def _fetch_from_web(self, keywords: str, limit: int) -> List[Dict]:
        """Fetch articles from web search (basic implementation)"""
        # This is a basic implementation - in production, you might use Google News API
        # or other news aggregation services
        articles = []
        
        # Example implementation using a simple news website
        try:
            search_url = f"https://news.google.com/rss/search?q={keywords}&hl=en&gl=US&ceid=US:en"
            feed = feedparser.parse(search_url)
            
            for entry in feed.entries[:limit]:
                content = self._extract_full_content(entry.get('link', ''))
                if content:
                    article = {
                        'title': entry.get('title', ''),
                        'content': content,
                        'description': entry.get('summary', ''),
                        'url': entry.get('link', ''),
                        'source': 'Google News',
                        'published_at': self._parse_date(entry.get('published')),
                        'author': 'Unknown'
                    }
                    articles.append(article)
                    
        except Exception as e:
            logger.error(f"Web search error: {str(e)}")
        
        logger.info(f"Fetched {len(articles)} articles from web search")
        return articles
    
    def _extract_full_content(self, url: str) -> Optional[str]:
        """Extract full article content from URL"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                element.decompose()
            
            # Try to find article content
            content_selectors = [
                'article', '.article-content', '.post-content', 
                '.entry-content', '[role="main"]', 'main'
            ]
            
            content = ""
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    content = ' '.join([elem.get_text() for elem in elements])
                    break
            
            if not content:
                # Fallback to all paragraph text
                paragraphs = soup.find_all('p')
                content = ' '.join([p.get_text() for p in paragraphs])
            
            return self._clean_content(content)
            
        except Exception as e:
            logger.error(f"Content extraction error for {url}: {str(e)}")
            return None
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize article content"""
        if not content:
            return ""
        
        # Remove extra whitespace and newlines
        content = re.sub(r'\s+', ' ', content)
        
        # Remove common unwanted phrases
        unwanted_phrases = [
            r'\[.*?\]',  # Remove text in brackets
            r'Click here.*?',
            r'Read more.*?',
            r'Subscribe.*?',
            r'Advertisement.*?'
        ]
        
        for phrase in unwanted_phrases:
            content = re.sub(phrase, '', content, flags=re.IGNORECASE)
        
        return content.strip()
    
    def _parse_date(self, date_str: str) -> str:
        """Parse and format date string"""
        if not date_str:
            return datetime.now().isoformat()
        
        try:
            # Try different date formats
            formats = [
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%dT%H:%M:%S%z',
                '%a, %d %b %Y %H:%M:%S %Z',
                '%a, %d %b %Y %H:%M:%S %z'
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.isoformat()
                except ValueError:
                    continue
            
            # If all parsing fails, return current time
            return datetime.now().isoformat()
            
        except Exception:
            return datetime.now().isoformat()
    
    def _remove_duplicates(self, articles: List[Dict]) -> List[Dict]:
        """Remove duplicate articles based on title similarity"""
        unique_articles = []
        seen_titles = set()
        
        for article in articles:
            title = article.get('title', '').lower().strip()
            
            # Create a simplified version for comparison
            simplified_title = re.sub(r'[^\w\s]', '', title)
            simplified_title = ' '.join(simplified_title.split())
            
            if simplified_title not in seen_titles and len(simplified_title) > 10:
                seen_titles.add(simplified_title)
                unique_articles.append(article)
        
        return unique_articles