$(document).ready(function() {
    // Initialize the application
    initializeApp();
    
    // Event listeners
    $('#analysisForm').on('submit', handleAnalysisSubmit);
    $('#refreshDashboard').on('click', refreshDashboard);
    
    // Smooth scrolling for navigation links
    $('a[href^="#"]').on('click', function(e) {
        e.preventDefault();
        const target = $($(this).attr('href'));
        if (target.length) {
            $('html, body').animate({
                scrollTop: target.offset().top - 100
            }, 500);
        }
    });
});

function initializeApp() {
    console.log('News Sentiment Analysis App Initialized');
    
    // Load dashboard data
    loadDashboardStats();
    
    // Add loading animation to buttons
    addButtonAnimations();
    
    // Initialize tooltips
    initializeTooltips();
}

function addButtonAnimations() {
    $('.btn').hover(
        function() {
            $(this).addClass('animate__animated animate__pulse');
        },
        function() {
            $(this).removeClass('animate__animated animate__pulse');
        }
    );
}

function initializeTooltips() {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

async function handleAnalysisSubmit(e) {
    e.preventDefault();
    
    const keywords = $('#keywords').val().trim();
    const sources = $('#sources').val() || ['rss'];
    const limit = parseInt($('#limit').val()) || 10;
    
    if (!keywords) {
        showAlert('Please enter keywords to analyze', 'warning');
        return;
    }
    
    try {
        showLoading();
        
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                keywords: keywords,
                sources: sources,
                limit: limit
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayResults(data);
            showAlert(`Successfully analyzed ${data.articles.length} articles!`, 'success');
        } else {
            throw new Error(data.error || 'Analysis failed');
        }
        
    } catch (error) {
        console.error('Analysis error:', error);
        showAlert(`Error: ${error.message}`, 'danger');
    } finally {
        hideLoading();
    }
}

function showLoading() {
    $('#loadingSpinner').fadeIn(300);
    $('#results').fadeOut(300);
    
    // Disable form
    $('#analysisForm input, #analysisForm select, #analysisForm button').prop('disabled', true);
}

function hideLoading() {
    $('#loadingSpinner').fadeOut(300);
    
    // Enable form
    $('#analysisForm input, #analysisForm select, #analysisForm button').prop('disabled', false);
}

function displayResults(data) {
    const { articles, summary } = data;
    
    // Show results section
    $('#results').fadeIn(500);
    
    // Update summary stats
    updateSummaryStats(summary);
    
    // Create charts
    createSentimentChart(summary);
    createConfidenceChart(articles);
    
    // Display articles
    displayArticles(articles);
    
    // Scroll to results
    $('html, body').animate({
        scrollTop: $('#results').offset().top - 100
    }, 500);
}

function updateSummaryStats(summary) {
    const statsHtml = `
        <div class="col-md-3 mb-3">
            <div class="card stats-card animate__animated animate__fadeInUp">
                <div class="stats-number text-primary">${summary.total_articles}</div>
                <div class="stats-label">Total Articles</div>
            </div>
        </div>
        <div class="col-md-3 mb-3">
            <div class="card stats-card animate__animated animate__fadeInUp animate__delay-1s">
                <div class="stats-number text-success">${summary.positive}</div>
                <div class="stats-label">Positive</div>
            </div>
        </div>
        <div class="col-md-3 mb-3">
            <div class="card stats-card animate__animated animate__fadeInUp animate__delay-2s">
                <div class="stats-number text-danger">${summary.negative}</div>
                <div class="stats-label">Negative</div>
            </div>
        </div>
        <div class="col-md-3 mb-3">
            <div class="card stats-card animate__animated animate__fadeInUp animate__delay-3s">
                <div class="stats-number text-warning">${summary.neutral}</div>
                <div class="stats-label">Neutral</div>
            </div>
        </div>
    `;
    
    $('#summaryStats').html(statsHtml);
}

function createSentimentChart(summary) {
    const data = [{
        values: [summary.positive, summary.negative, summary.neutral],
        labels: ['Positive', 'Negative', 'Neutral'],
        type: 'pie',
        hole: 0.4,
        marker: {
            colors: ['#10b981', '#ef4444', '#f59e0b']
        },
        textinfo: 'label+percent+value',
        textfont: {
            size: 14
        },
        hovertemplate: '<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
    }];
    
    const layout = {
        title: {
            text: 'Sentiment Distribution',
            font: {
                size: 18,
                family: 'Inter, sans-serif'
            }
        },
        showlegend: true,
        height: 400,
        margin: { t: 50, b: 20, l: 20, r: 20 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)'
    };
    
    const config = {
        responsive: true,
        displayModeBar: false
    };
    
    Plotly.newPlot('sentimentChart', data, layout, config);
}

function createConfidenceChart(articles) {
    const confidenceScores = articles.map(article => article.confidence);
    const sentiments = articles.map(article => article.sentiment);
    
    const data = [{
        x: confidenceScores,
        type: 'histogram',
        nbinsx: 20,
        marker: {
            color: '#2563eb',
            opacity: 0.7
        },
        hovertemplate: 'Confidence: %{x:.2f}<br>Count: %{y}<extra></extra>'
    }];
    
    const layout = {
        title: {
            text: 'Confidence Score Distribution',
            font: {
                size: 18,
                family: 'Inter, sans-serif'
            }
        },
        xaxis: {
            title: 'Confidence Score',
            range: [0, 1]
        },
        yaxis: {
            title: 'Number of Articles'
        },
        height: 400,
        margin: { t: 50, b: 50, l: 50, r: 20 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)'
    };
    
    const config = {
        responsive: true,
        displayModeBar: false
    };
    
    Plotly.newPlot('confidenceChart', data, layout, config);
}

function displayArticles(articles) {
    let articlesHtml = '';
    
    articles.forEach((article, index) => {
        const sentimentClass = `sentiment-${article.sentiment}`;
        const confidencePercentage = (article.confidence * 100).toFixed(1);
        const confidenceColor = getConfidenceColor(article.confidence);
        
        articlesHtml += `
            <div class="card article-card animate__animated animate__fadeInUp" style="animation-delay: ${index * 0.1}s">
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-8">
                            <h6 class="card-title mb-2">
                                <a href="${article.url}" target="_blank" class="text-decoration-none">
                                    ${article.title}
                                </a>
                            </h6>
                            <p class="card-text text-muted small mb-2">
                                ${article.description || 'No description available'}
                            </p>
                            <div class="d-flex align-items-center">
                                <small class="text-muted me-3">
                                    <i class="fas fa-globe me-1"></i>
                                    ${article.source}
                                </small>
                                <small class="text-muted me-3">
                                    <i class="fas fa-user me-1"></i>
                                    ${article.author || 'Unknown'}
                                </small>
                                <small class="text-muted">
                                    <i class="fas fa-clock me-1"></i>
                                    ${formatDate(article.published_at)}
                                </small>
                            </div>
                        </div>
                        <div class="col-md-4 text-end">
                            <div class="mb-2">
                                <span class="${sentimentClass}">
                                    <i class="fas fa-${getSentimentIcon(article.sentiment)} me-1"></i>
                                    ${article.sentiment.toUpperCase()}
                                </span>
                            </div>
                            <div class="mb-2">
                                <small class="text-muted">Confidence: ${confidencePercentage}%</small>
                                <div class="confidence-bar mt-1">
                                    <div class="confidence-fill" style="width: ${confidencePercentage}%; background-color: ${confidenceColor}"></div>
                                </div>
                            </div>
                            <div class="sentiment-scores">
                                <small class="d-block text-success">Positive: ${(article.scores.positive * 100).toFixed(1)}%</small>
                                <small class="d-block text-danger">Negative: ${(article.scores.negative * 100).toFixed(1)}%</small>
                                <small class="d-block text-warning">Neutral: ${(article.scores.neutral * 100).toFixed(1)}%</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    $('#articlesList').html(articlesHtml);
}

function getSentimentIcon(sentiment) {
    switch(sentiment) {
        case 'positive': return 'smile';
        case 'negative': return 'frown';
        case 'neutral': return 'meh';
        default: return 'question';
    }
}

function getConfidenceColor(confidence) {
    if (confidence >= 0.8) return '#10b981'; // Green
    if (confidence >= 0.6) return '#f59e0b'; // Yellow
    return '#ef4444'; // Red
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    
    return date.toLocaleDateString();
}

async function loadDashboardStats() {
    try {
        const response = await fetch('/api/history?days=7');
        const history = await response.json();
        
        if (Array.isArray(history)) {
            updateDashboardStats(history);
        }
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
    }
}

function updateDashboardStats(history) {
    const totalArticles = history.length;
    const avgConfidence = history.length > 0 
        ? ((history.reduce((sum, item) => sum + item.confidence, 0) / history.length) * 100).toFixed(1)
        : 0;
    const uniqueSources = new Set(history.map(item => item.source)).size;
    
    $('#totalArticles').text(totalArticles);
    $('#avgConfidence').text(`${avgConfidence}%`);
    $('#uniqueSources').text(uniqueSources);
}

async function refreshDashboard() {
    const button = $('#refreshDashboard');
    const icon = button.find('i');
    
    // Add spinning animation
    icon.addClass('fa-spin');
    button.prop('disabled', true);
    
    try {
        await loadDashboardStats();
        showAlert('Dashboard refreshed successfully!', 'success');
    } catch (error) {
        showAlert('Error refreshing dashboard', 'danger');
    } finally {
        // Remove spinning animation
        setTimeout(() => {
            icon.removeClass('fa-spin');
            button.prop('disabled', false);
        }, 1000);
    }
}

function showAlert(message, type = 'info') {
    const alertClass = `alert-${type}`;
    const iconClass = getAlertIcon(type);
    
    const alertHtml = `
        <div class="alert ${alertClass} alert-dismissible fade show animate__animated animate__fadeInDown" role="alert">
            <i class="fas fa-${iconClass} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // Remove existing alerts
    $('.alert').remove();
    
    // Add new alert to top of container
    $('.container').prepend(alertHtml);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        $('.alert').fadeOut(500, function() {
            $(this).remove();
        });
    }, 5000);
}

function getAlertIcon(type) {
    switch(type) {
        case 'success': return 'check-circle';
        case 'danger': return 'exclamation-triangle';
        case 'warning': return 'exclamation-circle';
        case 'info': return 'info-circle';
        default: return 'info-circle';
    }
}

// Add some interactive enhancements
$(document).on('mouseenter', '.card', function() {
    $(this).addClass('animate__animated animate__pulse');
}).on('mouseleave', '.card', function() {
    $(this).removeClass('animate__animated animate__pulse');
});

// Add loading states for all AJAX calls
$(document).ajaxStart(function() {
    $('body').addClass('loading');
}).ajaxStop(function() {
    $('body').removeClass('loading');
});

// Add keyboard shortcuts
$(document).keydown(function(e) {
    // Ctrl/Cmd + Enter to submit analysis form
    if ((e.ctrlKey || e.metaKey) && e.keyCode === 13) {
        e.preventDefault();
        $('#analysisForm').submit();
    }
    
    // Escape to clear form
    if (e.keyCode === 27) {
        $('#keywords').val('');
        $('#keywords').focus();
    }
});

// Add auto-focus to keywords input
$('#keywords').focus();

// Add real-time validation
$('#keywords').on('input', function() {
    const keywords = $(this).val().trim();
    const submitBtn = $('#analysisForm button[type="submit"]');
    
    if (keywords.length > 0) {
        submitBtn.removeClass('btn-secondary').addClass('btn-primary');
        $(this).removeClass('is-invalid').addClass('is-valid');
    } else {
        submitBtn.removeClass('btn-primary').addClass('btn-secondary');
        $(this).removeClass('is-valid').addClass('is-invalid');
    }
});

// Add progressive enhancement for modern browsers
if ('serviceWorker' in navigator) {
    // Could add service worker for offline functionality
    console.log('Service Worker supported');
}

// Add smooth animations for dynamically added content
const observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
        if (mutation.type === 'childList') {
            $(mutation.addedNodes).find('.animate__animated').each(function() {
                $(this).addClass('animate__fadeIn');
            });
        }
    });
});

observer.observe(document.body, {
    childList: true,
    subtree: true
});