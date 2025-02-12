import os
from fastapi import FastAPI
import csv
import datetime
import requests
from bs4 import BeautifulSoup
import html
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

app = FastAPI()

# Function to create a session with retries
def create_session():
    session = requests.Session()
    retry = Retry(
        total=5,
        read=5,
        connect=5,
        backoff_factor=0.3
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

session = create_session()

# Function to extract content from Bayut
def extract_content_bayut(url):
    response = session.get(url)
    response.encoding = 'utf-8'
    html_content = response.text
    soup = BeautifulSoup(html_content, 'html.parser')

    title = soup.find('h1', class_='entry-title').text.strip() if soup.find('h1', class_='entry-title') else "no title"
    publish_date = soup.find('div', class_='publishing-date').text.strip().replace('Published: ', '') if soup.find('div', class_='publishing-date') else "no date"
    meta_description = soup.find('meta', attrs={'name': 'description'})['content'] if soup.find('meta', attrs={'name': 'description'}) else "no description"
    canonical_link = soup.find('link', rel='canonical')['href'] if soup.find('link', rel='canonical') else "no link"

    article_content = []
    for element in soup.select('article .entry-content p, article .entry-content h1, article .entry-content h2, article .entry-content h3, article .entry-content h4, article .entry-content h5, article .entry-content h6, article .entry-content ul, article .entry-content ol, article .entry-content li'):
        article_content.append(element.get_text(strip=True))
    article_content = ' '.join(article_content) if article_content else "no content"

    yoast_schema_graph = soup.find('script', class_='yoast-schema-graph yoast-schema-graph--main').string if soup.find('script', class_='yoast-schema-graph yoast-schema-graph--main') else "no schema graph"

    title = html.unescape(title)
    publish_date = html.unescape(publish_date)
    meta_description = html.unescape(meta_description)
    canonical_link = html.unescape(canonical_link)
    article_content = html.unescape(article_content)
    yoast_schema_graph = html.unescape(yoast_schema_graph)

    data = {
        "Title": title,
        "Publish Date": publish_date,
        "Meta Description": meta_description,
        "Canonical Link": canonical_link,
        "Article Content": article_content,
        "Yoast Schema Graph": yoast_schema_graph
    }

    return data

# Function to extract content from Property Finder
def extract_content_property_finder(url):
    try:
        r = session.get(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'})
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')

        title_tag = soup.find("h1")
        date_tag = soup.find("p", class_="post-date")
        content_tag = soup.find(class_="entry-content")
        meta_description_tag = soup.find("meta", {"name": "description"})
        canonical_url_tag = soup.find("link", {"rel": "canonical"})
        yoast_schema_graph_tag = soup.find("script", {"class": "yoast-schema-graph", "type": "application/ld+json"})

        title = title_tag.text.strip() if title_tag else 'N/A'
        date = date_tag.text.strip() if date_tag else 'N/A'
        content = content_tag.get_text(strip=True) if content_tag else 'N/A'
        meta_description = meta_description_tag["content"] if meta_description_tag else 'N/A'
        canonical_url = canonical_url_tag["href"] if canonical_url_tag else 'N/A'
        yoast_schema_graph = yoast_schema_graph_tag.string.strip() if yoast_schema_graph_tag else 'N/A'

        data = {
            "Title": title,
            "Publish Date": date,
            "Meta Description": meta_description,
            "Canonical Link": canonical_url,
            "Article Content": content,
            "Yoast Schema Graph": yoast_schema_graph
        }
    except Exception as e:
        print(f"Error processing {url}: {e}")
        data = {
            "Title": 'N/A',
            "Publish Date": 'N/A',
            "Meta Description": 'N/A',
            "Canonical Link": 'N/A',
            "Article Content": 'N/A',
            "Yoast Schema Graph": 'N/A'
        }

    return data

@app.get("/{file}")
async def read_root(file: str):
    folder_path = "BlogsData"
    os.makedirs(folder_path, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(file))[0]
    linkFileToRead = os.path.join("LinkFiles", file)

    with open(linkFileToRead, 'r') as link_file:
        lines = link_file.readlines()
    formatted_links = [line.strip() for line in lines]

    current_datetime = datetime.datetime.now()
    timestamp = int(current_datetime.timestamp())
    csv_file = os.path.join(folder_path, f"{base_name}-{timestamp}.csv")

    all_data = []

    for url in formatted_links:
        try:
            if "bayut.com" in url:
                data = extract_content_bayut(url)
            elif "propertyfinder.ae" in url:
                data = extract_content_property_finder(url)
            else:
                continue
            all_data.append(data)
        except Exception as e:
            print(f"Error processing {url}: {e}")

    with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
        fieldnames = ["Title", "Publish Date", "Meta Description", "Canonical Link", "Article Content", "Yoast Schema Graph"]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_data)

    return {"Message": "Data extraction and storage complete.", "fileName": os.path.basename(csv_file)}
