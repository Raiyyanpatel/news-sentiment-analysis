from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from textblob import TextBlob
import numpy as np
import logging
from typing import Dict, List, Tuple
from config import Config
import re

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    """High-accuracy sentiment analyzer using ensemble of available models"""
    
    def __init__(self):
        self.models = {}
        self.vader_analyzer = SentimentIntensityAnalyzer()
        self._load_available_models()
    
    def _load_available_models(self):
        """Load available sentiment analysis models"""
        try:
            # Skip heavy transformer models for now - use only lightweight models
            logger.info("Using lightweight sentiment models (VADER + TextBlob)")
            self.models['vader'] = True
            self.models['textblob'] = True
            
            # Commented out transformer models to speed up startup
            # try:
            #     from transformers import pipeline
            #     logger.info("Loading RoBERTa sentiment model...")
            #     self.models['roberta'] = pipeline(
            #         "sentiment-analysis",
            #         model="cardiffnlp/twitter-roberta-base-sentiment-latest",
            #         return_all_scores=True
            #     )
            # logger.info("RoBERTa model loaded successfully")
            # except Exception as e:
            #     logger.warning(f"RoBERTa model not available: {e}")
            
            # Commented out for faster startup
            # # Try to load FinBERT if available
            # try:
            #     from transformers import pipeline
            #     logger.info("Loading FinBERT model...")
            #     self.models['finbert'] = pipeline(
            #         "sentiment-analysis",
            #         model="ProsusAI/finbert",
            #         return_all_scores=True
            #     )
            #     logger.info("FinBERT model loaded successfully")
            # except Exception as e:
            #     logger.warning(f"FinBERT model not available: {e}")
                
        except Exception as e:
            logger.warning(f"Transformer models not available: {e}")
        
        # Always have VADER and TextBlob as fallbacks
        logger.info("VADER and TextBlob models loaded successfully")
    
    def analyze(self, text: str) -> Dict:
        """
        Analyze sentiment using available models
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with sentiment results
        """
        if not text or len(text.strip()) < 10:
            return {
                'sentiment': 'neutral',
                'confidence': 0.5,
                'scores': {'positive': 0.33, 'negative': 0.33, 'neutral': 0.34},
                'details': 'Text too short for analysis'
            }
        
        # Preprocess text
        cleaned_text = self._preprocess_text(text)
        
        # Get predictions from all available models
        predictions = self._get_ensemble_predictions(cleaned_text)
        
        # Combine predictions using weighted ensemble
        final_sentiment, confidence, scores = self._ensemble_combine(predictions)
        
        return {
            'sentiment': final_sentiment,
            'confidence': round(confidence, 3),
            'scores': {
                'positive': round(scores.get('positive', 0), 3),
                'negative': round(scores.get('negative', 0), 3),
                'neutral': round(scores.get('neutral', 0), 3)
            },
            'details': {
                'model_predictions': predictions,
                'text_length': len(text),
                'processed_length': len(cleaned_text),
                'models_used': list(predictions.keys())
            }
        }
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for better sentiment analysis"""
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep punctuation that affects sentiment
        text = re.sub(r'[^\w\s.,!?;:-]', '', text)
        
        # Limit length for model processing
        max_length = 512
        if len(text) > max_length:
            # Try to cut at sentence boundary
            sentences = text.split('.')
            truncated = ""
            for sentence in sentences:
                if len(truncated + sentence) < max_length:
                    truncated += sentence + "."
                else:
                    break
            text = truncated if truncated else text[:max_length]
        
        return text.strip()
    
    def _get_ensemble_predictions(self, text: str) -> Dict:
        """Get predictions from all available models"""
        predictions = {}
        
        # RoBERTa prediction (if available)
        if 'roberta' in self.models:
            try:
                roberta_result = self.models['roberta'](text)[0]
                predictions['roberta'] = self._normalize_roberta_output(roberta_result)
            except Exception as e:
                logger.error(f"RoBERTa prediction error: {e}")
        
        # FinBERT prediction (if available)
        if 'finbert' in self.models:
            try:
                finbert_result = self.models['finbert'](text)[0]
                predictions['finbert'] = self._normalize_finbert_output(finbert_result)
            except Exception as e:
                logger.error(f"FinBERT prediction error: {e}")
        
        # VADER prediction (always available)
        try:
            vader_scores = self.vader_analyzer.polarity_scores(text)
            predictions['vader'] = self._normalize_vader_output(vader_scores)
        except Exception as e:
                logger.error(f"VADER prediction error: {e}")
        
        # TextBlob prediction (always available)
        try:
            blob = TextBlob(text)
            textblob_polarity = blob.sentiment.polarity
            predictions['textblob'] = self._normalize_textblob_output(textblob_polarity)
        except Exception as e:
            logger.error(f"TextBlob prediction error: {e}")
        
        return predictions
    
    def _normalize_roberta_output(self, result: List[Dict]) -> Dict:
        """Normalize RoBERTa output to standard format"""
        scores = {item['label'].lower(): item['score'] for item in result}
        
        # Map RoBERTa labels to standard format
        label_mapping = {
            'label_0': 'negative',
            'label_1': 'neutral', 
            'label_2': 'positive'
        }
        
        normalized_scores = {}
        for label, score in scores.items():
            mapped_label = label_mapping.get(label, label)
            normalized_scores[mapped_label] = score
        
        # Determine sentiment
        sentiment = max(normalized_scores, key=normalized_scores.get)
        confidence = normalized_scores[sentiment]
        
        return {
            'sentiment': sentiment,
            'confidence': confidence,
            'scores': normalized_scores
        }
    
    def _normalize_finbert_output(self, result: List[Dict]) -> Dict:
        """Normalize FinBERT output to standard format"""
        scores = {item['label'].lower(): item['score'] for item in result}
        sentiment = max(scores, key=scores.get)
        confidence = scores[sentiment]
        
        return {
            'sentiment': sentiment,
            'confidence': confidence,
            'scores': scores
        }
    
    def _normalize_vader_output(self, vader_scores: Dict) -> Dict:
        """Normalize VADER output to standard format"""
        compound = vader_scores['compound']
        
        # Convert compound score to sentiment
        if compound >= 0.05:
            sentiment = 'positive'
            confidence = abs(compound)
        elif compound <= -0.05:
            sentiment = 'negative'
            confidence = abs(compound)
        else:
            sentiment = 'neutral'
            confidence = 1 - abs(compound)
        
        # Normalize scores
        total = vader_scores['pos'] + vader_scores['neu'] + vader_scores['neg']
        scores = {
            'positive': vader_scores['pos'] / total if total > 0 else 0,
            'neutral': vader_scores['neu'] / total if total > 0 else 0,
            'negative': vader_scores['neg'] / total if total > 0 else 0
        }
        
        return {
            'sentiment': sentiment,
            'confidence': confidence,
            'scores': scores
        }
    
    def _normalize_textblob_output(self, polarity: float) -> Dict:
        """Normalize TextBlob output to standard format"""
        if polarity > 0.1:
            sentiment = 'positive'
            confidence = min(abs(polarity), 1.0)
        elif polarity < -0.1:
            sentiment = 'negative'
            confidence = min(abs(polarity), 1.0)
        else:
            sentiment = 'neutral'
            confidence = 1 - abs(polarity)
        
        # Create scores based on polarity
        pos_score = max(0, polarity)
        neg_score = max(0, -polarity)
        neu_score = 1 - pos_score - neg_score
        
        scores = {
            'positive': pos_score,
            'neutral': neu_score,
            'negative': neg_score
        }
        
        return {
            'sentiment': sentiment,
            'confidence': confidence,
            'scores': scores
        }
    
    def _ensemble_combine(self, predictions: Dict) -> Tuple[str, float, Dict]:
        """Combine predictions using weighted ensemble"""
        if not predictions:
            return 'neutral', 0.5, {'positive': 0.33, 'negative': 0.33, 'neutral': 0.34}
        
        # Model weights (higher weight = more trusted)
        weights = {
            'roberta': 0.40,      # Highest weight for RoBERTa
            'finbert': 0.30,      # High weight for FinBERT
            'vader': 0.20,        # Good weight for VADER
            'textblob': 0.10      # Lower weight for TextBlob
        }
        
        # Initialize combined scores
        combined_scores = {'positive': 0.0, 'negative': 0.0, 'neutral': 0.0}
        total_weight = 0.0
        
        # Combine predictions
        for model_name, prediction in predictions.items():
            weight = weights.get(model_name, 0.1)
            total_weight += weight
            
            for sentiment, score in prediction['scores'].items():
                combined_scores[sentiment] += score * weight
        
        # Normalize combined scores
        if total_weight > 0:
            for sentiment in combined_scores:
                combined_scores[sentiment] /= total_weight
        
        # Determine final sentiment and confidence
        final_sentiment = max(combined_scores, key=combined_scores.get)
        confidence = combined_scores[final_sentiment]
        
        # Apply confidence threshold
        if confidence < Config.CONFIDENCE_THRESHOLD:
            # If confidence is too low, classify as neutral
            final_sentiment = 'neutral'
            confidence = max(combined_scores['neutral'], 0.5)
        
        return final_sentiment, confidence, combined_scores
    
    def analyze_batch(self, texts: List[str]) -> List[Dict]:
        """Analyze sentiment for multiple texts"""
        results = []
        for text in texts:
            results.append(self.analyze(text))
        return results
    
    def get_model_info(self) -> Dict:
        """Get information about loaded models"""
        available_models = list(self.models.keys()) + ['vader', 'textblob']
        return {
            'available_models': available_models,
            'confidence_threshold': Config.CONFIDENCE_THRESHOLD,
            'ensemble_enabled': len(available_models) > 1,
            'transformer_models_loaded': len(self.models) > 0
        }