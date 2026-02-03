"""
Streamlit Web App - Carbon Measures RSS Feed Collector
No terminal required - runs in your browser!
"""

import streamlit as st
import feedparser
import pandas as pd
from datetime import datetime, timedelta
from urllib.parse import quote_plus
import time
import json
from dateutil import parser as date_parser

# Page configuration
st.set_page_config(
    page_title="Carbon Measures RSS Collector",
    page_icon="📰",
    layout="wide"
)

# Keywords to monitor
KEYWORDS = [
    "carbon measures",
    "scope 3 emissions",
    "exxon scope 3",
    "greenhouse gas protocol scope 3",
    "Amy Bracchio",
    "Karthik Ramanna"
]


@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_google_news_rss(keyword):
    """Fetch articles from Google News RSS for a specific keyword"""
    articles = []
    url = f"https://news.google.com/rss/search?q={quote_plus(keyword)}&hl=en-US&gl=US&ceid=US:en"
    
    try:
        feed = feedparser.parse(url)
        
        for entry in feed.entries:
            # Parse the published date
            published_str = entry.get('published', '')
            published_date = None
            
            try:
                if published_str:
                    published_date = date_parser.parse(published_str)
            except:
                pass
            
            article = {
                'Keyword': keyword,
                'Title': entry.get('title', ''),
                'URL': entry.get('link', ''),
                'Published': published_str,
                'Published_Date': published_date,
                'Source': entry.get('source', {}).get('title', 'Unknown'),
                'Description': entry.get('summary', '')
            }
            articles.append(article)
    except Exception as e:
        st.error(f"Error fetching {keyword}: {e}")
    
    return articles


def collect_all_feeds(progress_bar, status_text):
    """Collect RSS feeds for all keywords"""
    all_articles = []
    total_keywords = len(KEYWORDS)
    
    for i, keyword in enumerate(KEYWORDS):
        status_text.text(f"Fetching articles for: {keyword}")
        articles = fetch_google_news_rss(keyword)
        all_articles.extend(articles)
        progress_bar.progress((i + 1) / total_keywords)
        time.sleep(1)  # Be nice to Google's servers
    
    # Remove duplicates based on URL
    df = pd.DataFrame(all_articles)
    if not df.empty:
        df = df.drop_duplicates(subset=['URL'], keep='first')
    
    return df


def main():
    # Header
    st.title("📰 Carbon Measures RSS Feed Collector")
    st.markdown("Collect and analyze media coverage about Carbon Measures and related topics")
    
    # Sidebar
    st.sidebar.header("About")
    st.sidebar.info("""
    This app collects RSS feeds from Google News for keywords related to:
    - Carbon Measures initiative
    - Scope 3 emissions
    - Greenhouse gas protocols
    - Key people and organizations
    """)
    
    st.sidebar.header("Keywords Monitored")
    for i, keyword in enumerate(KEYWORDS, 1):
        st.sidebar.text(f"{i}. {keyword}")
    
    # Main content
    tab1, tab2, tab3 = st.tabs(["📥 Collect Feeds", "🔍 Search & Filter", "ℹ️ Instructions"])
    
    with tab1:
        st.header("Collect RSS Feeds")
        st.markdown("Click the button below to fetch the latest articles from Google News")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            collect_button = st.button("🚀 Collect Articles", type="primary", use_container_width=True)
        
        if collect_button:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            with st.spinner("Collecting RSS feeds..."):
                df = collect_all_feeds(progress_bar, status_text)
            
            progress_bar.empty()
            status_text.empty()
            
            if df.empty:
                st.warning("No articles found. Try again later.")
            else:
                # Store in session state
                st.session_state['articles_df'] = df
                st.session_state['collection_time'] = datetime.now()
                
                st.success(f"✅ Collection complete! Found {len(df)} unique articles")
                
                # Display summary
                st.subheader("📊 Summary")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Articles", len(df))
                with col2:
                    st.metric("Keywords Searched", len(KEYWORDS))
                with col3:
                    st.metric("Unique Sources", df['Source'].nunique())
                
                # Articles by keyword
                st.subheader("Articles by Keyword")
                keyword_counts = df['Keyword'].value_counts()
                st.bar_chart(keyword_counts)
                
                # Display articles
                st.subheader("📰 Recent Articles")
                display_df = df[['Title', 'Source', 'Keyword', 'Published', 'URL']].head(20)
                
                # Make URLs clickable
                st.dataframe(
                    display_df,
                    column_config={
                        "URL": st.column_config.LinkColumn("URL"),
                        "Title": st.column_config.TextColumn("Title", width="large"),
                    },
                    hide_index=True,
                    use_container_width=True
                )
                
                # Download buttons
                st.subheader("💾 Download Data")
                col1, col2 = st.columns(2)
                
                with col1:
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📄 Download CSV",
                        data=csv,
                        file_name=f"rss_feed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with col2:
                    json_str = df.to_json(orient='records', indent=2)
                    st.download_button(
                        label="📋 Download JSON",
                        data=json_str,
                        file_name=f"rss_feed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        use_container_width=True
                    )
    
    with tab2:
        st.header("Search & Filter Collected Data")
        
        if 'articles_df' not in st.session_state:
            st.info("👈 Please collect articles first using the 'Collect Feeds' tab")
        else:
            df = st.session_state['articles_df']
            collection_time = st.session_state['collection_time']
            
            st.text(f"Last collected: {collection_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Search
            search_term = st.text_input("🔍 Search in titles and descriptions", "")
            
            # Date filter
            st.subheader("📅 Date Filter")
            col1, col2 = st.columns(2)
            
            with col1:
                # Calculate min and max dates from data
                valid_dates = df[df['Published_Date'].notna()]['Published_Date']
                if len(valid_dates) > 0:
                    # Convert to datetime and remove timezone for date picker
                    valid_dates_dt = pd.to_datetime(valid_dates).dt.tz_localize(None)
                    min_date = valid_dates_dt.min().date()
                    max_date = valid_dates_dt.max().date()
                else:
                    min_date = datetime.now().date() - timedelta(days=30)
                    max_date = datetime.now().date()
                
                start_date = st.date_input(
                    "From date",
                    value=min_date,
                    min_value=min_date,
                    max_value=max_date
                )
            
            with col2:
                end_date = st.date_input(
                    "To date",
                    value=max_date,
                    min_value=min_date,
                    max_value=max_date
                )
            
            # Quick date filters
            st.write("Quick filters:")
            col1, col2, col3, col4 = st.columns(4)
            
            # Note: These buttons will update the date inputs in the next rerun
            quick_filter = None
            
            with col1:
                if st.button("Today"):
                    quick_filter = "today"
            
            with col2:
                if st.button("Last 7 days"):
                    quick_filter = "7days"
            
            with col3:
                if st.button("Last 30 days"):
                    quick_filter = "30days"
            
            with col4:
                if st.button("All time"):
                    quick_filter = "all"
            
            # Apply quick filter
            if quick_filter == "today":
                start_date = datetime.now().date()
                end_date = datetime.now().date()
            elif quick_filter == "7days":
                start_date = (datetime.now() - timedelta(days=7)).date()
                end_date = datetime.now().date()
            elif quick_filter == "30days":
                start_date = (datetime.now() - timedelta(days=30)).date()
                end_date = datetime.now().date()
            elif quick_filter == "all":
                if len(valid_dates) > 0:
                    valid_dates_dt = pd.to_datetime(valid_dates).dt.tz_localize(None)
                    start_date = valid_dates_dt.min().date()
                    end_date = valid_dates_dt.max().date()
            
            st.divider()
            
            # Keyword filter
            selected_keywords = st.multiselect(
                "Filter by keyword",
                options=df['Keyword'].unique().tolist(),
                default=df['Keyword'].unique().tolist()
            )
            
            # Source filter
            selected_sources = st.multiselect(
                "Filter by source",
                options=sorted(df['Source'].unique().tolist()),
                default=[]
            )
            
            # Apply filters
            filtered_df = df.copy()
            
            # Date filter
            if 'Published_Date' in filtered_df.columns:
                # Convert start and end dates to datetime for comparison
                start_datetime = pd.Timestamp(start_date)
                end_datetime = pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
                
                # Filter by date, keeping articles without dates
                date_mask = filtered_df['Published_Date'].isna()
                if filtered_df['Published_Date'].notna().any():
                    # Remove timezone info for comparison if present
                    filtered_df['Published_Date_Compare'] = pd.to_datetime(filtered_df['Published_Date']).dt.tz_localize(None)
                    date_mask = date_mask | (
                        (filtered_df['Published_Date_Compare'] >= start_datetime) & 
                        (filtered_df['Published_Date_Compare'] <= end_datetime)
                    )
                filtered_df = filtered_df[date_mask]
            
            if search_term:
                mask = (filtered_df['Title'].str.contains(search_term, case=False, na=False) | 
                       filtered_df['Description'].str.contains(search_term, case=False, na=False))
                filtered_df = filtered_df[mask]
            
            if selected_keywords:
                filtered_df = filtered_df[filtered_df['Keyword'].isin(selected_keywords)]
            
            if selected_sources:
                filtered_df = filtered_df[filtered_df['Source'].isin(selected_sources)]
            
            # Display results
            st.subheader(f"Results: {len(filtered_df)} articles")
            
            if len(filtered_df) > 0:
                display_df = filtered_df[['Title', 'Source', 'Keyword', 'Published', 'URL']]
                
                st.dataframe(
                    display_df,
                    column_config={
                        "URL": st.column_config.LinkColumn("URL"),
                        "Title": st.column_config.TextColumn("Title", width="large"),
                    },
                    hide_index=True,
                    use_container_width=True
                )
                
                # Download filtered results
                csv = filtered_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📄 Download Filtered Results (CSV)",
                    data=csv,
                    file_name=f"filtered_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No articles match your filters")
    
    with tab3:
        st.header("📖 How to Use This App")
        
        st.markdown("""
        ### Step-by-Step Instructions
        
        #### 1. Collect Articles
        - Go to the **"Collect Feeds"** tab
        - Click the **"🚀 Collect Articles"** button
        - Wait 10-20 seconds while articles are fetched
        - View the results and summary
        
        #### 2. Download Your Data
        After collection, you can download the data in two formats:
        - **CSV**: Open in Excel or Google Sheets
        - **JSON**: For programming or further processing
        
        #### 3. Search & Filter
        - Go to the **"Search & Filter"** tab
        - Search for specific terms
        - Filter by keyword or news source
        - Download filtered results
        
        ### Keywords Monitored
        This app searches for news articles containing:
        1. "carbon measures"
        2. "scope 3 emissions"
        3. "exxon scope 3"
        4. "greenhouse gas protocol scope 3"
        5. "Amy Bracchio"
        6. "Karthik Ramanna"
        
        ### Data Freshness
        - Articles are fetched from Google News RSS feeds
        - Data is cached for 1 hour to avoid excessive requests
        - Click "Collect Articles" again to refresh
        
        ### Tips
        - Collect articles regularly (daily or weekly) to track coverage over time
        - Download CSV files to build a database of articles
        - Use the search function to find specific topics or companies
        
        ### About Carbon Measures
        Carbon Measures is a global coalition of businesses working to establish 
        a more accurate carbon accounting framework and drive market-based solutions 
        to reduce emissions.
        
        Learn more at: https://www.carbonmeasures.org/
        """)
        
        st.divider()
        
        st.markdown("""
        ### Frequently Asked Questions
        
        **Q: How often should I collect articles?**  
        A: Daily or weekly, depending on how closely you want to monitor coverage.
        
        **Q: Can I collect historical articles?**  
        A: Google News RSS typically shows recent articles (last 24-48 hours).
        
        **Q: Why are some articles duplicated?**  
        A: The app removes exact URL duplicates, but the same story may appear 
        from different sources with different URLs.
        
        **Q: Can I add more keywords?**  
        A: Yes! If you're running this locally, edit the KEYWORDS list in the code.
        
        **Q: Is the data saved permanently?**  
        A: No, data resets when you refresh the page. Download CSV/JSON files to keep records.
        """)


if __name__ == "__main__":
    main()
