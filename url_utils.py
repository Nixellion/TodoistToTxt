import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time

def process_text_urls(text, timeout=10, delay=1):
    """
    Replace URLs in text with markdown format, attempting to fetch titles and descriptions.
    
    Args:
        text (str): Input text containing URLs
        timeout (int): Request timeout in seconds
        delay (float): Delay between requests in seconds
    
    Returns:
        tuple: (processed_text, descriptions_dict)
            - processed_text: Text with URLs replaced by markdown links
            - descriptions_dict: Dictionary mapping URLs to their descriptions
    """
    
    # Regex pattern to match URLs
    url_pattern = r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?'
    
    # Find all URLs in the text
    urls = re.findall(url_pattern, text)
    
    # Dictionary to store descriptions
    descriptions = {}
    
    # Process each unique URL
    processed_text = text
    for url in set(urls):  # Use set to avoid duplicate processing
        title, description = fetch_page_info(url, timeout)
        
        # Create markdown link
        if title:
            markdown_link = f"[{title}]({url})"
        else:
            markdown_link = f"[{url}]({url})"
        
        # Store description if found
        if description:
            descriptions[url] = description
        
        # Replace URL with markdown link in text
        processed_text = processed_text.replace(url, markdown_link)
        
        # Add delay between requests to be respectful
        if len(set(urls)) > 1:
            time.sleep(delay)
    
    return processed_text, descriptions

def fetch_page_info(url, timeout=10):
    """
    Fetch title and description from a webpage.
    
    Args:
        url (str): URL to fetch information from
        timeout (int): Request timeout in seconds
    
    Returns:
        tuple: (title, description) - both can be None if not found
    """
    try:
        # Set headers to mimic a browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title
        title = None
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()
        
        # Extract description (try multiple meta tags)
        description = None
        
        # Try og:description first
        og_desc = soup.find('meta', property='og:description')
        if og_desc:
            description = og_desc.get('content', '').strip()
        
        # Try meta description if og:description not found
        if not description:
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                description = meta_desc.get('content', '').strip()
        
        # Try twitter:description as fallback
        if not description:
            twitter_desc = soup.find('meta', attrs={'name': 'twitter:description'})
            if twitter_desc:
                description = twitter_desc.get('content', '').strip()
        
        return title, description
        
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None, None
    except Exception as e:
        print(f"Error parsing {url}: {e}")
        return None, None

# Example usage
if __name__ == "__main__":
    # Example text with URLs
    sample_text = """
    Check out this article: https://www.python.org/
    Also visit https://github.com/python/cpython for the source code.
    Here's another link: https://docs.python.org/3/
    """
    
    processed_text, descriptions = process_text_urls(sample_text)
    
    print("Original text:")
    print(sample_text)
    print("\nProcessed text:")
    print(processed_text)
    print("\nDescriptions found:")
    for url, desc in descriptions.items():
        print(f"- {url}: {desc}")