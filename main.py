import requests
from bs4 import BeautifulSoup
import pandas as pd
import logging
from colorama import Fore, Style, init
from tqdm import tqdm  # Import tqdm for the loading indicator

# Initialize colorama
init(autoreset=True)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Base URL of the website
BASE_URL = "https://www.scooter-center.com"

def get_soup(url):
    """Fetch the content of the URL and return a BeautifulSoup object."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    except requests.exceptions.RequestException as e:
        logger.error(Fore.RED + f"Error fetching {url}: {e}")
        return None

def is_valid_category(category_url):
    """Check if the category URL is valid by checking if the page contains products."""
    logger.info(f"Checking if category URL is valid: {category_url}")
    soup = get_soup(category_url)
    if soup is None:
        return False
    products = soup.find_all("div", class_="product--box box--minimal")
    is_valid = len(products) > 0
    if is_valid:
        logger.info(Fore.GREEN + "Valid category URL")
    else:
        logger.warning(Fore.YELLOW + "Invalid category URL")
    return is_valid

def get_total_pages(soup):
    """Extract the total number of pages from the pagination."""
    paging_info = soup.find("span", class_="paging--display")
    if paging_info:
        total_pages = paging_info.find("strong").text
        return int(total_pages)
    return 1

def scrape_category(category_url):
    """Scrape all products in a given category."""
    page = 1
    all_links = []
    all_products = []

    # Fetch the first page to get the total number of pages
    soup = get_soup(f"{category_url}?p=1&followSearch=9850&o=1&n=120")
    if soup is None:
        return all_products

    total_pages = get_total_pages(soup)
    logger.info(f"Total pages found: {total_pages}")

    while page <= total_pages:
        logger.info(f"Scraping page {page} of {total_pages}")
        url = f"{category_url}?p={page}&followSearch=9850&o=1&n=120"
        soup = get_soup(url)
        if soup is None:
            break

        # Find product containers
        product_containers = soup.find_all("div", class_="product--box box--minimal")
        if not product_containers:
            break

        for product in product_containers:
            product_link = product.find("a", class_="product--title")["href"]
            all_links.append(product_link)
        page += 1
    
    # Initialize tqdm for the loading indicator
    progress_bar = tqdm(all_links, desc="Scraping Products", unit="product")
    
    for link in progress_bar:
        product_data = scrape_product(link)
        if product_data:
            all_products.append(product_data)
    
    return all_products

def scrape_product(product_url):
    """Scrape the details of a single product."""
    soup = get_soup(product_url)
    if soup is None:
        return None

    # Get product title
    title_tag = soup.find("h1", class_="product--title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Get Part Number
    part_number_tag = soup.find("span", class_="entry--content", attrs={"itemprop": "sku"})
    part_number = part_number_tag.get_text(strip=True) if part_number_tag else ""

    # Get product price
    price_meta = soup.find("meta", itemprop="price")
    price = price_meta["content"] if price_meta else ""

    # Get product description
    description_tag = soup.find("div", class_="product--description")
    description = description_tag.get_text(strip=True) if description_tag else ""

    # Get product images
    image_tags = soup.select("div.image-slider--thumbnails-slide a.thumbnail--link img")
    images = [img["srcset"] for img in image_tags if img.has_attr("srcset")]    
    if len(images) > 0:
        image = images[0]
    else:
        image = ""

    return {
        "Title": title,
        "Part Number": part_number,
        "Price": price,
        "Desciption": description,
        "Image": image,    
        "URL": product_url
    }

def save_to_csv(products, filename):
    """Save the product data to a CSV file."""
    df = pd.DataFrame(products)
    df.to_csv(filename, index=False)
    logger.info(Fore.GREEN + f"Saved {len(products)} products to {filename}")

def main():
    category_url = input("Enter the category URL: ")
    # Remove the protocol and "www." from the URL
    url_without_protocol = category_url.replace("https://", "").replace("www.", "")

    # Split the URL by "/"
    url_parts = url_without_protocol.split("/")

    # Get the category, which is the third part
    category = url_parts[3]
    if is_valid_category(category_url):
        logger.info(Fore.GREEN + "Valid category. Scraping products...")

        products = scrape_category(category_url)
        save_to_csv(products, f"{category}.csv")
    else:
        logger.error(Fore.RED + "Invalid category URL. Please try again.")

if __name__ == "__main__":
    main()