#!/usr/bin/env python3
"""
Analytics Dashboard for Local Business Lead Generator.
Creates an HTML dashboard showing scraping statistics and business distribution.
"""

import os
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
import glob
from typing import Dict, List, Any

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
                'max': float(rating_data['rating'].max())
            }
    
    return stats


def create_html_dashboard(stats: Dict[str, Any], output_file: str = "dashboard.html"):
    """Create an HTML dashboard with statistics and charts."""
    
    # Generate category chart data
    category_data = ""
    if 'category_breakdown' in stats:
        categories = list(stats['category_breakdown'].keys())[:10]  # Top 10
        values = [stats['category_breakdown'][cat] for cat in categories]
        category_data = f"""
        <div class="chart-container">
            <h3>Top Business Categories</h3>
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
                    scales: {{
                        y: {{
                            beginAtZero: true
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
            <h3>Businesses by City</h3>
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
                    responsive: true
                }}
            }});
        </script>
        """
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Lead Generator Analytics Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                padding: 30px;
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 2px solid #e0e0e0;
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            .stat-card {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
            }}
            .stat-number {{
                font-size: 2.5em;
                font-weight: bold;
                margin-bottom: 5px;
            }}
            .stat-label {{
                font-size: 0.9em;
                opacity: 0.9;
            }}
            .chart-container {{
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }}
            .chart-container h3 {{
                margin-top: 0;
                color: #333;
            }}
            .summary-table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            .summary-table th, .summary-table td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            .summary-table th {{
                background-color: #f8f9fa;
                font-weight: 600;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #e0e0e0;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏢 Lead Generator Analytics Dashboard</h1>
                <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
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
            </div>
            
            {category_data}
            {city_data}
            
            <div class="chart-container">
                <h3>Data Quality Summary</h3>
                <table class="summary-table">
                    <tr>
                        <th>Metric</th>
                        <th>Count</th>
                        <th>Percentage</th>
                    </tr>
                    <tr>
                        <td>Total Businesses</td>
                        <td>{stats['total_businesses']:,}</td>
                        <td>100%</td>
                    </tr>
                    <tr>
                        <td>With Phone Numbers</td>
                        <td>{stats['with_phone']:,}</td>
                        <td>{(stats['with_phone'] / stats['total_businesses'] * 100):.1f}% if stats['total_businesses'] else "0.0%"</td>
                    </tr>
                    <tr>
                        <td>With Ratings</td>
                        <td>{stats['with_rating']:,}</td>
                        <td>{(stats['with_rating'] / stats['total_businesses'] * 100):.1f}% if stats['total_businesses'] else "0.0%"</td>
                    </tr>
                    <tr>
                        <td>With Hours</td>
                        <td>{stats['with_hours']:,}</td>
                        <td>{(stats['with_hours'] / stats['total_businesses'] * 100):.1f}% if stats['total_businesses'] else "0.0%"</td>
                    </tr>
                </table>
            </div>
            
            <div class="footer">
                <p>Generated by Local Business Lead Generator | {datetime.now().year}</p>
            </div>
        </div>
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
