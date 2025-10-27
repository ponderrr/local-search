#!/usr/bin/env python3
"""
Enhanced Analytics Dashboard for Local Business Lead Generator.
Creates an interactive HTML dashboard with advanced visualizations, dark mode, and export features.
"""

import os
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
import glob
from typing import Dict, List, Any
import numpy as np

from utils import setup_logging


def find_latest_leads_file(output_dir: str = "leads_output") -> str:
    """Find the most recent leads CSV file."""
    pattern = os.path.join(output_dir, "all_leads_no_website_*.csv")
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError(f"No leads files found in {output_dir}")
    return max(files, key=os.path.getctime)


def load_leads_data(csv_file: str) -> pd.DataFrame:
    """Load leads data from CSV file."""
    return pd.read_csv(csv_file)


def generate_statistics(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate comprehensive statistics from leads data."""
    stats = {
        'total_businesses': len(df),
        'cities': df['city'].nunique() if 'city' in df.columns else 0,
        'categories': df['category'].nunique() if 'category' in df.columns else 0,
        'with_phone': df['phone'].notna().sum() if 'phone' in df.columns else 0,
        'with_rating': df['rating'].notna().sum() if 'rating' in df.columns else 0,
        'with_hours': df['hours'].notna().sum() if 'hours' in df.columns else 0,
        'with_reviews': df['review_count'].notna().sum() if 'review_count' in df.columns else 0,
        'currently_open': df['currently_open'].eq('True').sum() if 'currently_open' in df.columns else 0,
        'with_price_level': df['price_level'].notna().sum() if 'price_level' in df.columns else 0,
    }
    
    # Category breakdown
    if 'category' in df.columns:
        stats['category_breakdown'] = df['category'].value_counts().to_dict()
    
    # City breakdown
    if 'city' in df.columns:
        stats['city_breakdown'] = df['city'].value_counts().to_dict()
    
    # Rating distribution
    if 'rating' in df.columns:
        rating_data = df[df['rating'].notna()]
        if not rating_data.empty:
            stats['rating_stats'] = {
                'average': float(rating_data['rating'].mean()),
                'median': float(rating_data['rating'].median()),
                'min': float(rating_data['rating'].min()),
                'max': float(rating_data['rating'].max()),
                'std': float(rating_data['rating'].std())
            }
            
            # Rating distribution histogram
            stats['rating_distribution'] = rating_data['rating'].value_counts().sort_index().to_dict()
    
    # Review count analysis
    if 'review_count' in df.columns:
        review_data = df[df['review_count'].notna() & (df['review_count'] > 0)]
        if not review_data.empty:
            stats['review_stats'] = {
                'average': float(review_data['review_count'].mean()),
                'median': float(review_data['review_count'].median()),
                'max': int(review_data['review_count'].max())
            }
    
    # Price level analysis
    if 'price_level' in df.columns:
        price_data = df[df['price_level'].notna() & (df['price_level'] != '')]
        if not price_data.empty:
            stats['price_level_breakdown'] = price_data['price_level'].value_counts().to_dict()
    
    # Business quality score (based on rating, reviews, hours)
    quality_scores = []
    for _, row in df.iterrows():
        score = 0
        if pd.notna(row.get('rating')) and row.get('rating', 0) > 0:
            score += min(row.get('rating', 0) * 20, 40)  # Max 40 points for rating
        if pd.notna(row.get('review_count')) and row.get('review_count', 0) > 0:
            score += min(np.log1p(row.get('review_count', 0)) * 5, 30)  # Max 30 points for reviews
        if pd.notna(row.get('hours')) and str(row.get('hours', '')).strip():
            score += 20  # 20 points for having hours
        if pd.notna(row.get('phone')) and str(row.get('phone', '')).strip():
            score += 10  # 10 points for having phone
        quality_scores.append(min(score, 100))  # Cap at 100
    
    if quality_scores:
        stats['quality_stats'] = {
            'average': float(np.mean(quality_scores)),
            'median': float(np.median(quality_scores)),
            'high_quality': sum(1 for s in quality_scores if s >= 70),
            'medium_quality': sum(1 for s in quality_scores if 40 <= s < 70),
            'low_quality': sum(1 for s in quality_scores if s < 40)
        }
    
    # Top businesses by quality
    df['quality_score'] = quality_scores
    top_businesses = df.nlargest(10, 'quality_score')[['name', 'city', 'rating', 'review_count', 'quality_score']].to_dict('records')
    stats['top_businesses'] = top_businesses
    
    return stats


def create_html_dashboard(stats: Dict[str, Any], output_file: str = "dashboard.html"):
    """Create an enhanced HTML dashboard with advanced visualizations, dark mode, and export features."""
    
    # Generate category chart data
    category_data = ""
    if 'category_breakdown' in stats:
        categories = list(stats['category_breakdown'].keys())[:10]  # Top 10
        values = [stats['category_breakdown'][cat] for cat in categories]
        category_data = f"""
        <div class="chart-container">
            <h3>📊 Top Business Categories</h3>
            <canvas id="categoryChart" width="400" height="200"></canvas>
        </div>
        <script>
            const categoryCtx = document.getElementById('categoryChart').getContext('2d');
            new Chart(categoryCtx, {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(categories)},
                    datasets: [{{
                        label: 'Number of Businesses',
                        data: {json.dumps(values)},
                        backgroundColor: 'rgba(54, 162, 235, 0.6)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{
                            labels: {{
                                color: 'var(--text-color)'
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            ticks: {{
                                color: 'var(--text-color)'
                            }},
                            grid: {{
                                color: 'var(--border-color)'
                            }}
                        }},
                        x: {{
                            ticks: {{
                                color: 'var(--text-color)'
                            }},
                            grid: {{
                                color: 'var(--border-color)'
                            }}
                        }}
                    }}
                }}
            }});
        </script>
        """
    
    # Generate city chart data
    city_data = ""
    if 'city_breakdown' in stats:
        cities = list(stats['city_breakdown'].keys())
        values = [stats['city_breakdown'][city] for city in cities]
        city_data = f"""
        <div class="chart-container">
            <h3>🏙️ Businesses by City</h3>
            <canvas id="cityChart" width="400" height="200"></canvas>
        </div>
        <script>
            const cityCtx = document.getElementById('cityChart').getContext('2d');
            new Chart(cityCtx, {{
                type: 'doughnut',
                data: {{
                    labels: {json.dumps(cities)},
                    datasets: [{{
                        data: {json.dumps(values)},
                        backgroundColor: [
                            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
                            '#FF9F40', '#FF6384', '#C9CBCF', '#4BC0C0', '#FF6384'
                        ]
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{
                            labels: {{
                                color: 'var(--text-color)'
                            }}
                        }}
                    }}
                }}
            }});
        </script>
        """
    
    # Rating distribution chart
    rating_chart = ""
    if 'rating_distribution' in stats:
        ratings = list(stats['rating_distribution'].keys())
        counts = [stats['rating_distribution'][r] for r in ratings]
        rating_chart = f"""
        <div class="chart-container">
            <h3>⭐ Rating Distribution</h3>
            <canvas id="ratingChart" width="400" height="200"></canvas>
        </div>
        <script>
            const ratingCtx = document.getElementById('ratingChart').getContext('2d');
            new Chart(ratingCtx, {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(ratings)},
                    datasets: [{{
                        label: 'Number of Businesses',
                        data: {json.dumps(counts)},
                        backgroundColor: 'rgba(255, 193, 7, 0.6)',
                        borderColor: 'rgba(255, 193, 7, 1)',
                        borderWidth: 1
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{
                            labels: {{
                                color: 'var(--text-color)'
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            ticks: {{
                                color: 'var(--text-color)'
                            }},
                            grid: {{
                                color: 'var(--border-color)'
                            }}
                        }},
                        x: {{
                            ticks: {{
                                color: 'var(--text-color)'
                            }},
                            grid: {{
                                color: 'var(--border-color)'
                            }}
                        }}
                    }}
                }}
            }});
        </script>
        """
    
    # Quality score chart
    quality_chart = ""
    if 'quality_stats' in stats:
        quality_stats = stats['quality_stats']
        quality_chart = f"""
        <div class="chart-container">
            <h3>🎯 Business Quality Distribution</h3>
            <canvas id="qualityChart" width="400" height="200"></canvas>
        </div>
        <script>
            const qualityCtx = document.getElementById('qualityChart').getContext('2d');
            new Chart(qualityCtx, {{
                type: 'doughnut',
                data: {{
                    labels: ['High Quality (70+)', 'Medium Quality (40-69)', 'Low Quality (<40)'],
                    datasets: [{{
                        data: [{quality_stats['high_quality']}, {quality_stats['medium_quality']}, {quality_stats['low_quality']}],
                        backgroundColor: ['#28a745', '#ffc107', '#dc3545']
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{
                            labels: {{
                                color: 'var(--text-color)'
                            }}
                        }}
                    }}
                }}
            }});
        </script>
        """
    
    # Price level chart
    price_chart = ""
    if 'price_level_breakdown' in stats:
        prices = list(stats['price_level_breakdown'].keys())
        counts = [stats['price_level_breakdown'][p] for p in prices]
        price_chart = f"""
        <div class="chart-container">
            <h3>💰 Price Level Distribution</h3>
            <canvas id="priceChart" width="400" height="200"></canvas>
        </div>
        <script>
            const priceCtx = document.getElementById('priceChart').getContext('2d');
            new Chart(priceCtx, {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(prices)},
                    datasets: [{{
                        label: 'Number of Businesses',
                        data: {json.dumps(counts)},
                        backgroundColor: 'rgba(40, 167, 69, 0.6)',
                        borderColor: 'rgba(40, 167, 69, 1)',
                        borderWidth: 1
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{
                            labels: {{
                                color: 'var(--text-color)'
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            ticks: {{
                                color: 'var(--text-color)'
                            }},
                            grid: {{
                                color: 'var(--border-color)'
                            }}
                        }},
                        x: {{
                            ticks: {{
                                color: 'var(--text-color)'
                            }},
                            grid: {{
                                color: 'var(--border-color)'
                            }}
                        }}
                    }}
                }}
            }});
        </script>
        """
    
    # Top businesses table
    top_businesses_table = ""
    if 'top_businesses' in stats and stats['top_businesses']:
        table_rows = ""
        for i, business in enumerate(stats['top_businesses'], 1):
            table_rows += f"""
            <tr>
                <td>{i}</td>
                <td>{business['name']}</td>
                <td>{business['city']}</td>
                <td>{business.get('rating', 'N/A')}</td>
                <td>{business.get('review_count', 'N/A')}</td>
                <td>{business.get('quality_score', 0):.1f}</td>
            </tr>
            """
        
        top_businesses_table = f"""
        <div class="chart-container">
            <h3>🏆 Top 10 Businesses by Quality Score</h3>
            <div class="table-responsive">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Business Name</th>
                            <th>City</th>
                            <th>Rating</th>
                            <th>Reviews</th>
                            <th>Quality Score</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
            </div>
        </div>
        """
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🎯 Lead Generator Analytics Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            :root {{
                --bg-color: #ffffff;
                --text-color: #333333;
                --border-color: #e0e0e0;
                --card-bg: #ffffff;
                --shadow: 0 2px 10px rgba(0,0,0,0.1);
                --primary-color: #667eea;
                --secondary-color: #764ba2;
            }}
            
            [data-theme="dark"] {{
                --bg-color: #1a1a1a;
                --text-color: #ffffff;
                --border-color: #333333;
                --card-bg: #2d2d2d;
                --shadow: 0 2px 10px rgba(0,0,0,0.3);
                --primary-color: #7c3aed;
                --secondary-color: #a855f7;
            }}
            
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
                color: var(--text-color);
                min-height: 100vh;
                transition: all 0.3s ease;
            }}
            
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                padding: 20px;
            }}
            
            .header {{
                text-align: center;
                margin-bottom: 30px;
                padding: 30px;
                background: var(--card-bg);
                border-radius: 15px;
                box-shadow: var(--shadow);
                position: relative;
            }}
            
            .theme-toggle {{
                position: absolute;
                top: 20px;
                right: 20px;
                background: var(--primary-color);
                color: white;
                border: none;
                padding: 10px 15px;
                border-radius: 25px;
                cursor: pointer;
                font-size: 14px;
                transition: all 0.3s ease;
            }}
            
            .theme-toggle:hover {{
                transform: scale(1.05);
            }}
            
            .header h1 {{
                font-size: 2.5em;
                margin-bottom: 10px;
                background: linear-gradient(45deg, var(--primary-color), var(--secondary-color));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }}
            
            .header p {{
                color: var(--text-color);
                opacity: 0.8;
                font-size: 1.1em;
            }}
            
            .export-buttons {{
                margin-top: 20px;
                display: flex;
                gap: 10px;
                justify-content: center;
                flex-wrap: wrap;
            }}
            
            .export-btn {{
                background: var(--primary-color);
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 25px;
                cursor: pointer;
                font-size: 14px;
                transition: all 0.3s ease;
                text-decoration: none;
                display: inline-block;
            }}
            
            .export-btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            }}
            
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            
            .stat-card {{
                background: var(--card-bg);
                padding: 25px;
                border-radius: 15px;
                text-align: center;
                box-shadow: var(--shadow);
                transition: transform 0.3s ease;
                border: 1px solid var(--border-color);
            }}
            
            .stat-card:hover {{
                transform: translateY(-5px);
            }}
            
            .stat-number {{
                font-size: 2.5em;
                font-weight: bold;
                margin-bottom: 10px;
                background: linear-gradient(45deg, var(--primary-color), var(--secondary-color));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }}
            
            .stat-label {{
                font-size: 0.9em;
                opacity: 0.8;
                color: var(--text-color);
            }}
            
            .charts-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            
            .chart-container {{
                background: var(--card-bg);
                padding: 25px;
                border-radius: 15px;
                box-shadow: var(--shadow);
                border: 1px solid var(--border-color);
            }}
            
            .chart-container h3 {{
                margin-bottom: 20px;
                color: var(--text-color);
                font-size: 1.3em;
            }}
            
            .data-table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
            }}
            
            .data-table th, .data-table td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid var(--border-color);
                color: var(--text-color);
            }}
            
            .data-table th {{
                background-color: var(--primary-color);
                color: white;
                font-weight: 600;
                position: sticky;
                top: 0;
            }}
            
            .data-table tr:hover {{
                background-color: rgba(102, 126, 234, 0.1);
            }}
            
            .table-responsive {{
                max-height: 400px;
                overflow-y: auto;
                border-radius: 10px;
                border: 1px solid var(--border-color);
            }}
            
            .summary-section {{
                background: var(--card-bg);
                padding: 25px;
                border-radius: 15px;
                box-shadow: var(--shadow);
                margin-bottom: 20px;
                border: 1px solid var(--border-color);
            }}
            
            .summary-section h3 {{
                margin-bottom: 20px;
                color: var(--text-color);
            }}
            
            .summary-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 15px;
            }}
            
            .summary-item {{
                padding: 15px;
                background: rgba(102, 126, 234, 0.1);
                border-radius: 10px;
                border-left: 4px solid var(--primary-color);
            }}
            
            .summary-item strong {{
                color: var(--primary-color);
            }}
            
            .footer {{
                text-align: center;
                margin-top: 30px;
                padding: 20px;
                color: var(--text-color);
                opacity: 0.8;
            }}
            
            @media (max-width: 768px) {{
                .charts-grid {{
                    grid-template-columns: 1fr;
                }}
                
                .stats-grid {{
                    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                }}
                
                .header h1 {{
                    font-size: 2em;
                }}
                
                .export-buttons {{
                    flex-direction: column;
                    align-items: center;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <button class="theme-toggle" onclick="toggleTheme()">🌙 Dark Mode</button>
                <h1>🎯 Lead Generator Analytics Dashboard</h1>
                <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <div class="export-buttons">
                    <button class="export-btn" onclick="exportToPDF()">📄 Export PDF</button>
                    <button class="export-btn" onclick="exportToExcel()">📊 Export Excel</button>
                    <button class="export-btn" onclick="printDashboard()">🖨️ Print</button>
                </div>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">{stats['total_businesses']:,}</div>
                    <div class="stat-label">Total Businesses</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{stats['cities']}</div>
                    <div class="stat-label">Cities Searched</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{stats['categories']}</div>
                    <div class="stat-label">Business Categories</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{stats['with_phone']:,}</div>
                    <div class="stat-label">With Phone Numbers</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{stats['with_rating']:,}</div>
                    <div class="stat-label">With Ratings</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{stats['with_hours']:,}</div>
                    <div class="stat-label">With Hours</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{stats.get('with_reviews', 0):,}</div>
                    <div class="stat-label">With Reviews</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{stats.get('currently_open', 0):,}</div>
                    <div class="stat-label">Currently Open</div>
                </div>
            </div>
            
            <div class="charts-grid">
                {category_data}
                {city_data}
                {rating_chart}
                {quality_chart}
                {price_chart}
            </div>
            
            {top_businesses_table}
            
            <div class="summary-section">
                <h3>📈 Data Quality Summary</h3>
                <div class="summary-grid">
                    <div class="summary-item">
                        <strong>Total Businesses:</strong> {stats['total_businesses']:,}
                    </div>
                    <div class="summary-item">
                        <strong>Phone Coverage:</strong> {(stats['with_phone'] / stats['total_businesses'] * 100):.1f}% if stats['total_businesses'] else "0.0%"
                    </div>
                    <div class="summary-item">
                        <strong>Rating Coverage:</strong> {(stats['with_rating'] / stats['total_businesses'] * 100):.1f}% if stats['total_businesses'] else "0.0%"
                    </div>
                    <div class="summary-item">
                        <strong>Hours Coverage:</strong> {(stats['with_hours'] / stats['total_businesses'] * 100):.1f}% if stats['total_businesses'] else "0.0%"
                    </div>
                    <div class="summary-item">
                        <strong>Average Rating:</strong> {stats.get('rating_stats', {}).get('average', 0):.2f}
                    </div>
                    <div class="summary-item">
                        <strong>Average Quality Score:</strong> {stats.get('quality_stats', {}).get('average', 0):.1f}
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <p>Generated by Local Business Lead Generator | {datetime.now().year}</p>
            </div>
        </div>
        
        <script>
            // Theme toggle functionality
            function toggleTheme() {{
                const body = document.body;
                const themeToggle = document.querySelector('.theme-toggle');
                
                if (body.getAttribute('data-theme') === 'dark') {{
                    body.removeAttribute('data-theme');
                    themeToggle.textContent = '🌙 Dark Mode';
                }} else {{
                    body.setAttribute('data-theme', 'dark');
                    themeToggle.textContent = '☀️ Light Mode';
                }}
            }}
            
            // Export functions
            function exportToPDF() {{
                window.print();
            }}
            
            function exportToExcel() {{
                alert('Excel export feature would be implemented here. For now, you can copy the data from the dashboard.');
            }}
            
            function printDashboard() {{
                window.print();
            }}
            
            // Initialize charts with theme support
            Chart.defaults.color = 'var(--text-color)';
            Chart.defaults.borderColor = 'var(--border-color)';
        </script>
    </body>
    </html>
    """
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return output_file


def main():
    """Main function to generate analytics dashboard."""
    logger = setup_logging()
    
    try:
        # Find latest leads file
        leads_file = find_latest_leads_file()
        logger.info(f"Loading data from: {leads_file}")
        
        # Load and analyze data
        df = load_leads_data(leads_file)
        stats = generate_statistics(df)
        
        # Generate dashboard
        dashboard_file = create_html_dashboard(stats)
        
        logger.info(f"Analytics dashboard created: {dashboard_file}")
        logger.info(f"Total businesses analyzed: {stats['total_businesses']:,}")
        logger.info(f"Cities: {stats['cities']}, Categories: {stats['categories']}")
        
        print(f"\n🎯 Analytics Dashboard Ready!")
        print(f"📊 File: {os.path.abspath(dashboard_file)}")
        print(f"🌐 Open in your browser to view interactive charts")
        
    except FileNotFoundError as e:
        logger.error(f"Error: {e}")
        print("❌ No leads files found. Please run the scraper first.")
    except Exception as e:
        logger.error(f"Error generating dashboard: {e}")
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
