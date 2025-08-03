import sqlite3
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from config import Config
import os

logger = logging.getLogger(__name__)

class DataManager:
    """Manages data storage and retrieval for sentiment analysis"""
    
    def __init__(self):
        self.db_path = Config.DATABASE_PATH
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with required tables"""
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create analysis table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS analysis_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        keywords TEXT NOT NULL,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        description TEXT,
                        url TEXT,
                        source TEXT,
                        author TEXT,
                        published_at TEXT,
                        sentiment TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        positive_score REAL NOT NULL,
                        negative_score REAL NOT NULL,
                        neutral_score REAL NOT NULL,
                        model_details TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create summary table for quick analytics
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS analysis_summary (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        keywords TEXT NOT NULL,
                        date TEXT NOT NULL,
                        total_articles INTEGER DEFAULT 0,
                        positive_count INTEGER DEFAULT 0,
                        negative_count INTEGER DEFAULT 0,
                        neutral_count INTEGER DEFAULT 0,
                        avg_confidence REAL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(keywords, date)
                    )
                ''')
                
                # Create indexes for better performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_keywords ON analysis_results(keywords)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_sentiment ON analysis_results(sentiment)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON analysis_results(created_at)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_published_at ON analysis_results(published_at)')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise
    
    def store_analysis(self, keywords: str, articles: List[Dict]) -> bool:
        """Store analysis results in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Store individual articles
                for article in articles:
                    cursor.execute('''
                        INSERT INTO analysis_results (
                            keywords, title, content, description, url, source, author,
                            published_at, sentiment, confidence, positive_score,
                            negative_score, neutral_score, model_details
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        keywords,
                        article.get('title', ''),
                        article.get('content', ''),
                        article.get('description', ''),
                        article.get('url', ''),
                        article.get('source', ''),
                        article.get('author', ''),
                        article.get('published_at', ''),
                        article.get('sentiment', ''),
                        article.get('confidence', 0),
                        article.get('scores', {}).get('positive', 0),
                        article.get('scores', {}).get('negative', 0),
                        article.get('scores', {}).get('neutral', 0),
                        json.dumps(article.get('details', {}))
                    ))
                
                # Update summary
                self._update_summary(cursor, keywords, articles)
                
                conn.commit()
                logger.info(f"Stored {len(articles)} articles for keywords: {keywords}")
                return True
                
        except Exception as e:
            logger.error(f"Error storing analysis: {e}")
            return False
    
    def _update_summary(self, cursor, keywords: str, articles: List[Dict]):
        """Update daily summary statistics"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Calculate statistics
        total_articles = len(articles)
        positive_count = len([a for a in articles if a.get('sentiment') == 'positive'])
        negative_count = len([a for a in articles if a.get('sentiment') == 'negative'])
        neutral_count = len([a for a in articles if a.get('sentiment') == 'neutral'])
        avg_confidence = sum([a.get('confidence', 0) for a in articles]) / len(articles) if articles else 0
        
        # Insert or update summary
        cursor.execute('''
            INSERT OR REPLACE INTO analysis_summary (
                keywords, date, total_articles, positive_count, negative_count,
                neutral_count, avg_confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (keywords, today, total_articles, positive_count, negative_count, neutral_count, avg_confidence))
    
    def get_history(self, days: int = 7) -> List[Dict]:
        """Get analysis history for the last N days"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT keywords, sentiment, confidence, created_at, title, source
                    FROM analysis_results 
                    WHERE date(created_at) >= ?
                    ORDER BY created_at DESC
                    LIMIT 100
                '''
                
                cursor.execute(query, (cutoff_date,))
                results = cursor.fetchall()
                
                history = []
                for row in results:
                    history.append({
                        'keywords': row[0],
                        'sentiment': row[1],
                        'confidence': row[2],
                        'created_at': row[3],
                        'title': row[4],
                        'source': row[5]
                    })
                
                return history
                
        except Exception as e:
            logger.error(f"Error getting history: {e}")
            return []
    
    def get_trends(self, keyword: str, days: int = 7) -> Dict:
        """Get sentiment trends for a specific keyword"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get daily trends
                query = '''
                    SELECT 
                        date(created_at) as date,
                        sentiment,
                        COUNT(*) as count,
                        AVG(confidence) as avg_confidence
                    FROM analysis_results 
                    WHERE keywords LIKE ? AND date(created_at) >= ?
                    GROUP BY date(created_at), sentiment
                    ORDER BY date(created_at)
                '''
                
                cursor.execute(query, (f'%{keyword}%', cutoff_date))
                results = cursor.fetchall()
                
                # Organize data by date
                trends = {}
                for row in results:
                    date, sentiment, count, avg_conf = row
                    if date not in trends:
                        trends[date] = {'positive': 0, 'negative': 0, 'neutral': 0, 'total': 0}
                    
                    trends[date][sentiment] = count
                    trends[date]['total'] += count
                
                # Convert to list format
                trend_list = []
                for date, data in sorted(trends.items()):
                    trend_list.append({
                        'date': date,
                        'positive': data['positive'],
                        'negative': data['negative'],
                        'neutral': data['neutral'],
                        'total': data['total'],
                        'positive_pct': (data['positive'] / data['total'] * 100) if data['total'] > 0 else 0,
                        'negative_pct': (data['negative'] / data['total'] * 100) if data['total'] > 0 else 0,
                        'neutral_pct': (data['neutral'] / data['total'] * 100) if data['total'] > 0 else 0
                    })
                
                return {
                    'keyword': keyword,
                    'period_days': days,
                    'trends': trend_list
                }
                
        except Exception as e:
            logger.error(f"Error getting trends: {e}")
            return {'keyword': keyword, 'period_days': days, 'trends': []}
    
    def get_summary_stats(self, keywords: str = None, days: int = 7) -> Dict:
        """Get summary statistics"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Base query
                where_clause = "WHERE date(created_at) >= ?"
                params = [cutoff_date]
                
                if keywords:
                    where_clause += " AND keywords LIKE ?"
                    params.append(f'%{keywords}%')
                
                query = f'''
                    SELECT 
                        COUNT(*) as total_articles,
                        SUM(CASE WHEN sentiment = 'positive' THEN 1 ELSE 0 END) as positive_count,
                        SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) as negative_count,
                        SUM(CASE WHEN sentiment = 'neutral' THEN 1 ELSE 0 END) as neutral_count,
                        AVG(confidence) as avg_confidence,
                        COUNT(DISTINCT keywords) as unique_keywords,
                        COUNT(DISTINCT source) as unique_sources
                    FROM analysis_results {where_clause}
                '''
                
                cursor.execute(query, params)
                result = cursor.fetchone()
                
                if result and result[0] > 0:
                    total = result[0]
                    return {
                        'total_articles': total,
                        'positive_count': result[1],
                        'negative_count': result[2],
                        'neutral_count': result[3],
                        'positive_percentage': (result[1] / total * 100) if total > 0 else 0,
                        'negative_percentage': (result[2] / total * 100) if total > 0 else 0,
                        'neutral_percentage': (result[3] / total * 100) if total > 0 else 0,
                        'avg_confidence': round(result[4] or 0, 3),
                        'unique_keywords': result[5],
                        'unique_sources': result[6],
                        'period_days': days
                    }
                else:
                    return {
                        'total_articles': 0,
                        'positive_count': 0,
                        'negative_count': 0,
                        'neutral_count': 0,
                        'positive_percentage': 0,
                        'negative_percentage': 0,
                        'neutral_percentage': 0,
                        'avg_confidence': 0,
                        'unique_keywords': 0,
                        'unique_sources': 0,
                        'period_days': days
                    }
                
        except Exception as e:
            logger.error(f"Error getting summary stats: {e}")
            return {}
    
    def get_top_keywords(self, days: int = 7, limit: int = 10) -> List[Dict]:
        """Get most analyzed keywords"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT 
                        keywords,
                        COUNT(*) as article_count,
                        AVG(confidence) as avg_confidence,
                        SUM(CASE WHEN sentiment = 'positive' THEN 1 ELSE 0 END) as positive_count,
                        SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) as negative_count
                    FROM analysis_results 
                    WHERE date(created_at) >= ?
                    GROUP BY keywords
                    ORDER BY article_count DESC
                    LIMIT ?
                '''
                
                cursor.execute(query, (cutoff_date, limit))
                results = cursor.fetchall()
                
                top_keywords = []
                for row in results:
                    keywords, count, avg_conf, pos_count, neg_count = row
                    top_keywords.append({
                        'keywords': keywords,
                        'article_count': count,
                        'avg_confidence': round(avg_conf or 0, 3),
                        'positive_count': pos_count,
                        'negative_count': neg_count,
                        'sentiment_ratio': (pos_count - neg_count) / count if count > 0 else 0
                    })
                
                return top_keywords
                
        except Exception as e:
            logger.error(f"Error getting top keywords: {e}")
            return []
    
    def export_data(self, keywords: str = None, days: int = 7, format: str = 'json') -> Optional[str]:
        """Export analysis data to JSON or CSV"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            with sqlite3.connect(self.db_path) as conn:
                where_clause = "WHERE date(created_at) >= ?"
                params = [cutoff_date]
                
                if keywords:
                    where_clause += " AND keywords LIKE ?"
                    params.append(f'%{keywords}%')
                
                query = f'''
                    SELECT * FROM analysis_results {where_clause}
                    ORDER BY created_at DESC
                '''
                
                df = pd.read_sql_query(query, conn, params=params)
                
                if format.lower() == 'csv':
                    return df.to_csv(index=False)
                else:
                    return df.to_json(orient='records', indent=2)
                
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            return None
    
    def cleanup_old_data(self, days: int = 30):
        """Clean up old data to manage database size"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Delete old records
                cursor.execute('DELETE FROM analysis_results WHERE date(created_at) < ?', (cutoff_date,))
                cursor.execute('DELETE FROM analysis_summary WHERE date < ?', (cutoff_date,))
                
                # Vacuum database to reclaim space
                cursor.execute('VACUUM')
                
                conn.commit()
                logger.info(f"Cleaned up data older than {days} days")
                
        except Exception as e:
            logger.error(f"Error cleaning up data: {e}")