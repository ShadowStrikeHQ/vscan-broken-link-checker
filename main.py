import argparse
import requests
from bs4 import BeautifulSoup
import logging
import urllib.parse
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_argparse():
    """
    Sets up the argument parser for the command line interface.
    """
    parser = argparse.ArgumentParser(description='vscan-broken-link-checker: Identifies broken links in a website or HTML document.')
    parser.add_argument('url', help='The URL or local HTML file to scan.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output (debug logging).')
    parser.add_argument('-t', '--timeout', type=int, default=10, help='Set timeout for HTTP requests in seconds (default: 10).')
    parser.add_argument('-o', '--output', type=str, help='Output file to save the results (optional).')
    parser.add_argument('--ignore-ssl', action='store_true', help='Ignore SSL certificate verification errors.') # Potentially insecure, but useful for testing.
    return parser

def is_valid_url(url):
    """
    Validates if a given string is a valid URL.
    Prevents common issues like protocol missing, or invalid characters
    """
    try:
        result = urllib.parse.urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def get_all_links(url, html):
    """
    Extracts all links from an HTML document.

    Args:
        url (str): The base URL of the page. Used to resolve relative URLs.
        html (str): The HTML content of the page.

    Returns:
        set: A set of unique URLs found in the HTML.
    """
    soup = BeautifulSoup(html, 'html.parser')
    links = set()
    for a_tag in soup.find_all('a', href=True):
        link = a_tag['href']
        absolute_url = urllib.parse.urljoin(url, link)  # Handles relative and absolute URLs correctly
        links.add(absolute_url)
    return links

def check_link_status(url, timeout=10, ignore_ssl=False):
    """
    Checks the HTTP status code of a given URL.

    Args:
        url (str): The URL to check.
        timeout (int): Timeout for the HTTP request in seconds.
        ignore_ssl (bool):  Whether to ignore SSL certificate verification errors.

    Returns:
        tuple: A tuple containing the URL and its HTTP status code.  Returns (url, None) if error.
    """
    try:
        if ignore_ssl:
            response = requests.get(url, timeout=timeout, verify=False)
        else:
            response = requests.get(url, timeout=timeout)
        return url, response.status_code
    except requests.exceptions.RequestException as e:
        logging.error(f"Error checking {url}: {e}")
        return url, None

def scan_website(url, timeout=10, ignore_ssl=False):
    """
    Scans a website for broken links.

    Args:
        url (str): The URL of the website to scan.
        timeout (int): Timeout for HTTP requests in seconds.
        ignore_ssl (bool): Whether to ignore SSL certificate verification errors.

    Returns:
        dict: A dictionary where keys are URLs and values are their HTTP status codes.
    """
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        html = response.text
        links = get_all_links(url, html)
        results = {}
        for link in links:
            link_url, status_code = check_link_status(link, timeout, ignore_ssl)
            results[link_url] = status_code
        return results
    except requests.exceptions.RequestException as e:
        logging.error(f"Error accessing {url}: {e}")
        return {}

def scan_html_file(file_path, base_url="http://localhost", timeout=10, ignore_ssl=False):
    """
    Scans a local HTML file for broken links.

    Args:
        file_path (str): The path to the HTML file.
        base_url (str):  The base URL to use for resolving relative links.
        timeout (int): Timeout for HTTP requests in seconds.
        ignore_ssl (bool): Whether to ignore SSL certificate verification errors.

    Returns:
        dict: A dictionary where keys are URLs and values are their HTTP status codes.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            html = f.read()
        links = get_all_links(base_url, html)
        results = {}
        for link in links:
            link_url, status_code = check_link_status(link, timeout, ignore_ssl)
            results[link_url] = status_code
        return results
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        return {}
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {e}")
        return {}

def main():
    """
    Main function to execute the broken link checker.
    """
    parser = setup_argparse()
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG) # Set log level to debug

    url = args.url

    if not url:
        print("Error: Please provide a URL or file path to scan.")
        sys.exit(1)

    if url.lower().startswith(("http://", "https://")):
        if not is_valid_url(url):
             print("Error: Invalid URL provided.")
             sys.exit(1)
        results = scan_website(url, args.timeout, args.ignore_ssl)
    else:
        # Assume it's a file path
        results = scan_html_file(url, timeout=args.timeout, ignore_ssl=args.ignore_ssl)

    broken_links = {url: status for url, status in results.items() if status is None or status >= 400}

    if broken_links:
        print("Broken links found:")
        for url, status in broken_links.items():
            print(f"  {url}: {status if status is not None else 'Error'}")

        if args.output:
            try:
                with open(args.output, 'w') as f:
                    for url, status in broken_links.items():
                        f.write(f"{url}: {status if status is not None else 'Error'}\n")
                print(f"Results saved to {args.output}")
            except Exception as e:
                logging.error(f"Error writing to output file: {e}")

    else:
        print("No broken links found.")

if __name__ == "__main__":
    main()

# Usage Examples:
#
# 1. Scan a website:
#    python main.py https://www.example.com
#
# 2. Scan a website with verbose output:
#    python main.py https://www.example.com -v
#
# 3. Scan a website with a timeout of 5 seconds:
#    python main.py https://www.example.com -t 5
#
# 4. Scan a website and save the results to a file:
#    python main.py https://www.example.com -o broken_links.txt
#
# 5. Scan a local HTML file:
#    python main.py index.html
#
# 6.  Ignore SSL errors when scanning (USE WITH CAUTION, ONLY FOR TESTING):
#    python main.py https://self-signed.example.com --ignore-ssl
#
# Offensive Tools Steps (Hypothetical):
# This tool by itself is primarily for information gathering.  However, the results could be used to:
# 1.  Identify potential "dead" areas on a website to deface/modify.
# 2.  Discover admin or API endpoints that return 404/403, which might be misconfigurations or unintended exposures.
# 3.  Map the application structure and identify potential areas for further testing/exploitation.