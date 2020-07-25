import argparse
import logging
import sys
import re
import numpy as np
from queue import PriorityQueue
from urllib import parse, request
from dataclasses import dataclass

import pandas as pd
import requests
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))

@dataclass
class Listing:
    city: str
    shelters: list


def parse_links(root, html):
    soup = BeautifulSoup(html, 'html.parser')
    for link in soup.find_all('a'):
        href = link.get('href')
        if href:
            text = link.string
            if not text:
                text = ''
            text = re.sub(r'\s+', ' ', text).strip()
            yield parse.urljoin(root, link.get('href')), text


def get_links(url):
    res = request.urlopen(url)
    return list(parse_links(url, res.read()))


def get_domain(url):
    return parse.urlparse(url).netloc + parse.urlparse(url).path #'/'.join(parse.urlparse(url).path.split('/')[:2])


def get_non_self_referencing(url):
    """
    Get a list of links on the page specificed by the url,
    but only keep non-local links and non self-references.
    Return a list of (link, title) pairs, just like get_links()
    """

    args = get_args()
    domain = get_domain(args.site)
    links = get_links(url)
    filtered = []
    for link, title in links:
        if get_domain(link) == domain:
            if len(parse.urlparse(link).fragment) == 0:
                filtered.append((link, title))  # get non self-referencing
    return filtered

def get_shelters(url):
    for link, title in get_links(url):
        if 'shelter.cgi' in get_domain(link) and len(parse.urlparse(link).fragment) == 0:
            yield (link, title)


def crawl(root, max_iterations, within_domain, wanted_content=None):
    """
    Crawl the url specified by `root`.
    `wanted_content` is a list of content types to crawl
    `within_domain` specifies whether the crawler should limit itself to the domain of `root`
    """
    queue = PriorityQueue()
    queue.put((1, root))
    iteration = 0

    visited = []
    listings = []

    df = pd.DataFrame(columns=['url', 'title', 'body'])

    while not queue.empty():
        url = queue.get()[1]
        if url in visited:
            continue
        if iteration >= max_iterations:
            break
        logger.info(f'URL: {url}')
        try:
            req = request.urlopen(url)

            content_type = req.info().get_content_type()
            if wanted_content and content_type not in wanted_content:
                continue
            visited.append(url)
            iteration += 1

            city = ', '.join(re.findall(r'=(\w+)', parse.urlparse(url).query))
            shelters = set(get_shelters(url))
            listings.append(Listing(city, shelters))
            logger.info(f'{len(shelters)} shelters found in {city}')

            for link, title in get_non_self_referencing(url):
                if link not in visited:
                    priority = int(1)
                    queue.put((priority, link))

        except Exception as e:
            logger.error(e, url)

    return listings

def has_bold_content(tag):
    for child in tag.children:
        if isinstance(child, Tag):
            if child.name =='b':
                return True
    return False

def scrape(url, city):
    phone, website, last_updated = None, None, None
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')
    name = soup.find('h3').get_text()

    contact = soup.find('div', {'class': 'col col_6_of_12'}).find('p').get_text().strip().split()
    idx = np.where(np.array(contact) == ':')[0]
    address = ' '.join(contact[:idx[0]])
    if len(idx) == 1:
        classes = [value for value in soup.find('div', {'class': 'col col_6_of_12'}).find('p').find_all('i')]
        if np.any(['phone' in c for c in classes]):
            phone = ' '.join(contact[idx[0]+1:])
        else:
            website = ' '.join(contact[idx[0]+1:])
    else:
        phone = ' '.join(contact[idx[0]+1:idx[1]])
        website = ' '.join(contact[idx[1]+1:])

    for p in soup.find_all('p'):
        if has_bold_content(p) and p.find('b').get_text() == 'Description:':
            description = ' '.join(p.get_text().split()).split()
            description = ' '.join(description[description.index('Description:')+1:])
            try:
                last_updated = description.split('Shelter Information Last Update Date: ')[1]
                description = '.'.join(description.split('.')[:-1]) + '.'
            except:
                pass
    logger.info(f'Scraped {name}')
    return pd.DataFrame({'name': [name], 'city': [city], 'address': [address], 'phone': [phone],  
        'website': [website], 'description': [description], 'last_updated': [last_updated]})

def scrape_all(listings):
    df = pd.DataFrame(columns=['name', 'city', 'contact', 'address', 'phone', 'website', 'description', 'last_updated'])
    for listing in listings:
        for shelter, name in listing.shelters:
            df = pd.concat([df, scrape(shelter, listing.city)])
    return df


def get_args():
    parser = argparse.ArgumentParser(description="Web crawler")
    parser.add_argument('--site', help='The URL to crawl', type=str,
                        default='https://www.homelessshelterdirectory.org/cgi-bin/id/city.cgi?city=Boston&state=MA')
    parser.add_argument('--max-iterations', help='Maximum number of iterations to scrape', type=int, default=1)
    args = parser.parse_args()
    return args


def main():
    args = get_args()
    listings = crawl(args.site, args.max_iterations, True)
    df = scrape_all(listings)
    df.to_csv('scraped_shelters.csv', index=False)


if __name__ == '__main__':
    main()
