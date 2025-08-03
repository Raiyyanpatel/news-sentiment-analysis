import plotly.graph_objs as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List
from src.data_manager import DataManager
import logging

logger = logging.getLogger(__name__)

def create_sentiment_chart(keyword: str, days: int = 7) -> Dict:
    """Create sentiment distribution pie chart"""
    try:
        data_manager = DataManager()
        stats = data_manager.get_summary_stats(keyword, days)
        
        if stats.get('total_articles', 0) == 0:
            return {'error': 'No data available for the specified period'}
        
        # Create pie chart
        labels = ['Positive', 'Negative', 'Neutral']
        values = [
            stats.get('positive_count', 0),
            stats.get('negative_count', 0),
            stats.get('neutral_count', 0)
        ]
        colors = ['#28a745', '#dc3545', '#6c757d']
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.4,
            marker_colors=colors,
            textinfo='label+percent+value',
            textfont_size=12,
            hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
        )])
        
        fig.update_layout(
            title={
                'text': f'Sentiment Distribution for "{keyword}"<br><sub>Last {days} days - {stats["total_articles"]} articles</sub>',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 16}
            },
            showlegend=True,
            width=500,
            height=400,
            margin=dict(t=80, b=20, l=20, r=20)
        )
        
        return {
            'chart': json.loads(json.dumps(fig, cls=PlotlyJSONEncoder)),
            'stats': stats
        }
        
    except Exception as e:
        logger.error(f"Error creating sentiment chart: {e}")
        return {'error': str(e)}

def create_trend_chart(keyword: str, days: int = 7) -> Dict:
    """Create sentiment trend line chart"""
    try:
        data_manager = DataManager()
        trends_data = data_manager.get_trends(keyword, days)
        
        if not trends_data.get('trends'):
            return {'error': 'No trend data available for the specified period'}
        
        trends = trends_data['trends']
        
        # Prepare data
        dates = [trend['date'] for trend in trends]
        positive_pcts = [trend['positive_pct'] for trend in trends]
        negative_pcts = [trend['negative_pct'] for trend in trends]
        neutral_pcts = [trend['neutral_pct'] for trend in trends]
        
        # Create line chart
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=dates, y=positive_pcts,
            mode='lines+markers',
            name='Positive',
            line=dict(color='#28a745', width=3),
            marker=dict(size=8),
            hovertemplate='Date: %{x}<br>Positive: %{y:.1f}%<extra></extra>'
        ))
        
        fig.add_trace(go.Scatter(
            x=dates, y=negative_pcts,
            mode='lines+markers',
            name='Negative',
            line=dict(color='#dc3545', width=3),
            marker=dict(size=8),
            hovertemplate='Date: %{x}<br>Negative: %{y:.1f}%<extra></extra>'
        ))
        
        fig.add_trace(go.Scatter(
            x=dates, y=neutral_pcts,
            mode='lines+markers',
            name='Neutral',
            line=dict(color='#6c757d', width=3),
            marker=dict(size=8),
            hovertemplate='Date: %{x}<br>Neutral: %{y:.1f}%<extra></extra>'
        ))
        
        fig.update_layout(
            title={
                'text': f'Sentiment Trends for "{keyword}"<br><sub>Last {days} days</sub>',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 16}
            },
            xaxis_title='Date',
            yaxis_title='Percentage (%)',
            hovermode='x unified',
            width=800,
            height=400,
            margin=dict(t=80, b=50, l=50, r=20),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        # Style the chart
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)', range=[0, 100])
        
        return {
            'chart': json.loads(json.dumps(fig, cls=PlotlyJSONEncoder)),
            'trends': trends_data
        }
        
    except Exception as e:
        logger.error(f"Error creating trend chart: {e}")
        return {'error': str(e)}

def create_volume_chart(days: int = 7) -> Dict:
    """Create article volume chart by source"""
    try:
        data_manager = DataManager()
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Get volume data by source
        import sqlite3
        with sqlite3.connect(data_manager.db_path) as conn:
            query = '''
                SELECT 
                    source,
                    date(created_at) as date,
                    COUNT(*) as article_count
                FROM analysis_results 
                WHERE date(created_at) >= ?
                GROUP BY source, date(created_at)
                ORDER BY date(created_at), source
            '''
            
            df = pd.read_sql_query(query, conn, params=[cutoff_date])
        
        if df.empty:
            return {'error': 'No volume data available'}
        
        # Create stacked bar chart
        fig = px.bar(
            df, 
            x='date', 
            y='article_count', 
            color='source',
            title=f'Article Volume by Source (Last {days} days)',
            labels={'article_count': 'Number of Articles', 'date': 'Date'},
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        
        fig.update_layout(
            xaxis_title='Date',
            yaxis_title='Number of Articles',
            title_x=0.5,
            width=800,
            height=400,
            margin=dict(t=60, b=50, l=50, r=20)
        )
        
        return {
            'chart': json.loads(json.dumps(fig, cls=PlotlyJSONEncoder)),
            'data': df.to_dict('records')
        }
        
    except Exception as e:
        logger.error(f"Error creating volume chart: {e}")
        return {'error': str(e)}

def create_confidence_distribution(keyword: str = None, days: int = 7) -> Dict:
    """Create confidence score distribution histogram"""
    try:
        data_manager = DataManager()
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        import sqlite3
        with sqlite3.connect(data_manager.db_path) as conn:
            where_clause = "WHERE date(created_at) >= ?"
            params = [cutoff_date]
            
            if keyword:
                where_clause += " AND keywords LIKE ?"
                params.append(f'%{keyword}%')
            
            query = f'''
                SELECT confidence, sentiment
                FROM analysis_results {where_clause}
            '''
            
            df = pd.read_sql_query(query, conn, params=params)
        
        if df.empty:
            return {'error': 'No confidence data available'}
        
        # Create histogram
        fig = px.histogram(
            df, 
            x='confidence', 
            color='sentiment',
            title=f'Confidence Score Distribution{f" for {keyword}" if keyword else ""} (Last {days} days)',
            labels={'confidence': 'Confidence Score', 'count': 'Number of Articles'},
            color_discrete_map={
                'positive': '#28a745',
                'negative': '#dc3545', 
                'neutral': '#6c757d'
            },
            nbins=20
        )
        
        fig.update_layout(
            xaxis_title='Confidence Score',
            yaxis_title='Number of Articles',
            title_x=0.5,
            width=700,
            height=400,
            margin=dict(t=60, b=50, l=50, r=20)
        )
        
        return {
            'chart': json.loads(json.dumps(fig, cls=PlotlyJSONEncoder)),
            'avg_confidence': df['confidence'].mean(),
            'total_articles': len(df)
        }
        
    except Exception as e:
        logger.error(f"Error creating confidence distribution: {e}")
        return {'error': str(e)}

def create_keyword_comparison(keywords_list: List[str], days: int = 7) -> Dict:
    """Create comparison chart between multiple keywords"""
    try:
        data_manager = DataManager()
        
        comparison_data = []
        for keyword in keywords_list:
            stats = data_manager.get_summary_stats(keyword, days)
            if stats.get('total_articles', 0) > 0:
                comparison_data.append({
                    'keyword': keyword,
                    'positive_pct': stats.get('positive_percentage', 0),
                    'negative_pct': stats.get('negative_percentage', 0),
                    'neutral_pct': stats.get('neutral_percentage', 0),
                    'total_articles': stats.get('total_articles', 0),
                    'avg_confidence': stats.get('avg_confidence', 0)
                })
        
        if not comparison_data:
            return {'error': 'No data available for comparison'}
        
        df = pd.DataFrame(comparison_data)
        
        # Create grouped bar chart
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Positive',
            x=df['keyword'],
            y=df['positive_pct'],
            marker_color='#28a745',
            hovertemplate='Keyword: %{x}<br>Positive: %{y:.1f}%<extra></extra>'
        ))
        
        fig.add_trace(go.Bar(
            name='Negative',
            x=df['keyword'],
            y=df['negative_pct'],
            marker_color='#dc3545',
            hovertemplate='Keyword: %{x}<br>Negative: %{y:.1f}%<extra></extra>'
        ))
        
        fig.add_trace(go.Bar(
            name='Neutral',
            x=df['keyword'],
            y=df['neutral_pct'],
            marker_color='#6c757d',
            hovertemplate='Keyword: %{x}<br>Neutral: %{y:.1f}%<extra></extra>'
        ))
        
        fig.update_layout(
            title={
                'text': f'Keyword Sentiment Comparison (Last {days} days)',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 16}
            },
            xaxis_title='Keywords',
            yaxis_title='Percentage (%)',
            barmode='group',
            width=800,
            height=500,
            margin=dict(t=80, b=50, l=50, r=20),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        return {
            'chart': json.loads(json.dumps(fig, cls=PlotlyJSONEncoder)),
            'comparison_data': comparison_data
        }
        
    except Exception as e:
        logger.error(f"Error creating keyword comparison: {e}")
        return {'error': str(e)}

def create_summary_dashboard(days: int = 7) -> Dict:
    """Create a comprehensive dashboard summary"""
    try:
        data_manager = DataManager()
        
        # Get overall stats
        overall_stats = data_manager.get_summary_stats(days=days)
        top_keywords = data_manager.get_top_keywords(days=days, limit=5)
        
        # Create combined visualization
        dashboard_data = {
            'overall_stats': overall_stats,
            'top_keywords': top_keywords,
            'charts': {}
        }
        
        # Add volume chart
        volume_chart = create_volume_chart(days)
        if 'chart' in volume_chart:
            dashboard_data['charts']['volume'] = volume_chart
        
        # Add confidence distribution
        confidence_chart = create_confidence_distribution(days=days)
        if 'chart' in confidence_chart:
            dashboard_data['charts']['confidence'] = confidence_chart
        
        # Add top keywords comparison if we have data
        if top_keywords:
            keywords_list = [kw['keywords'] for kw in top_keywords[:3]]
            comparison_chart = create_keyword_comparison(keywords_list, days)
            if 'chart' in comparison_chart:
                dashboard_data['charts']['comparison'] = comparison_chart
        
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Error creating dashboard: {e}")
        return {'error': str(e)}