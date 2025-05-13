# import re
# import scrapy


# class IndianExpressSpider(scrapy.Spider):
#     name = "IndianExpressSpider"
#     allowed_domains = ["indianexpress.com"]
#     start_urls = ['https://indianexpress.com/section/india/']

#     def parse(self, response):
#         # First article
#         first_article = response.css('div.first')
#         if first_article:
#             yield from self.extract_article(first_article, response)

#         # Other articles
#         articles = response.css('div.articles div.articles')
#         for article in articles:
#             yield from self.extract_article(article, response)

#         # Handle pagination up to page 5
#         current_page = int(re.search(
#             r'/page/(\d+)/', response.url).group(1)) if '/page/' in response.url else 1
#         if current_page < 5:
#             next_page = f'https://indianexpress.com/section/india/page/{current_page + 1}/'
#             yield scrapy.Request(next_page, callback=self.parse)

#     def extract_article(self, article, response):
#         link = article.css('div.snaps a::attr(href)').get()
#         image_url = article.css('div.snaps img::attr(src)').get()
#         headline = article.css('div.img-context h2.title a::text').get()
#         description = article.css('div.img-context p::text').get()
#         published_date = article.css('div.img-context .date::text').get()

#         if link:
#             yield response.follow(link, callback=self.parse_article, meta={
#                 'headline': headline,
#                 'description': description,
#                 'url': link,
#                 'published_date': published_date,
#                 'image_url': image_url
#             })

#     def parse_article(self, response):
#         content_blocks = response.css(
#             'div#pcl-full-content p::text, div#pcl-full-content p *::text').getall()
#         content = ' '.join([text.strip()
#                            for text in content_blocks if text.strip()])
#         author = response.css('a[rel="author"]::text').get()
#         tags = response.css('div.tags a::text').getall()

#         yield {
#             "headline": response.meta.get("headline"),
#             "description": response.meta.get("description"),
#             "url": response.meta.get("url"),
#             "last_updated": None,
#             "category": response.url.split('/')[3] if len(response.url.split('/')) > 3 else None,
#             "image_url": response.meta.get("image_url"),
#             "author": author,
#             "published_date": response.meta.get("published_date"),
#             "source": "indianexpress.com",
#             "content": content if content else None,
#             "tags": tags if tags else None,
#         }

# import scrapy
# import re


# class IndianExpressSpider(scrapy.Spider):
#     name = "indianexpress"
#     allowed_domains = ["indianexpress.com"]
#     start_urls = ['https://indianexpress.com/section/india/']

#     def parse(self, response):
#         # First article
#         first_article = response.css('div.first')
#         if first_article:
#             yield from self.extract_article(first_article, response)

#         # Other articles
#         articles = response.css('div.articles > div.articles')
#         for article in articles:
#             yield from self.extract_article(article, response)

#         # Pagination logic up to page 5
#         current_page = int(re.search(
#             r'/page/(\d+)/', response.url).group(1)) if '/page/' in response.url else 1
#         if current_page < 5:
#             next_page = f'https://indianexpress.com/section/india/page/{current_page + 1}/'
#             yield scrapy.Request(next_page, callback=self.parse)

#     def extract_article(self, article, response):
#         link = article.css('div.snaps a::attr(href)').get()
#         image_url = article.css('div.snaps img::attr(src)').get()
#         headline = article.css('div.img-context h2.title a::text').get()
#         description = article.css('div.img-context p::text').get()
#         published_date = article.css('div.img-context .date::text').get()

#         if link:
#             yield response.follow(link, callback=self.parse_article, meta={
#                 'headline': headline,
#                 'description': description,
#                 'url': link,
#                 'published_date': published_date,
#                 'image_url': image_url
#             })

#     def parse_article(self, response):
#         content_blocks = response.css(
#             'div#pcl-full-content p::text, div#pcl-full-content p *::text').getall()
#         content = ' '.join([text.strip()
#                            for text in content_blocks if text.strip()])
#         author = response.css('a[rel="author"]::text').get()
#         tags = response.css('div.tags a::text').getall()

#         yield {
#             "headline": response.meta.get("headline"),
#             "description": response.meta.get("description"),
#             "url": response.meta.get("url"),
#             "last_updated": None,
#             "category": response.url.split('/')[3] if len(response.url.split('/')) > 3 else None,
#             "image_url": response.meta.get("image_url"),
#             "author": author,
#             "published_date": response.meta.get("published_date"),
#             "source": "indianexpress.com",
#             "content": content if content else None,
#             "tags": tags if tags else None,
#         }

import scrapy


class IndianExpressSpider(scrapy.Spider):
    name = "indianexpress"
    start_urls = [
        f'https://indianexpress.com/section/india/page/{i}/' for i in range(1, 6)]

    def parse(self, response):
        # Select both 'article.first' and 'div.articles > div'
        first_article = response.css('article.first')
        if first_article:
            yield from self.extract_article(first_article, response)

        articles = response.css('div.articles > div')
        for article in articles:
            yield from self.extract_article(article, response)

    def extract_article(self, article, response):
        link = article.css('div.snaps a::attr(href)').get()
        image_url = article.css('div.snaps img::attr(src)').get()
        # headline = article.css(
        #     'div.img-context h2.title  a::attr(title)').get()
        # description = article.css('div.img-context p::text').get()
        published_date = article.css('div.img-context .date::text').get()

        if link:
            yield response.follow(link, callback=self.parse_article, meta={
                # 'headline': headline,
                # 'description': description,
                'url': link,
                'published_date': published_date,
                'image_url': image_url
            })

    def parse_article(self, response):
        # Extract content
        content_paragraphs = response.css(
            'div#pcl-full-content p::text, div#pcl-full-content p *::text'
        ).getall()
        content = ' '.join([para.strip()
                           for para in content_paragraphs if para.strip()])

        # Extract headline from article page
        headline_article = response.css('h1[itemprop="headline"]::text').get()
        if not headline_article:  # Fallback to another common selector if the first fails
            headline_article = response.css(
                'h1.native_story_title::text').get()

        # Extract description from article page
        description_article = response.css(
            'h2[itemprop="description"]::text').get()
        if not description_article:  # Fallback to another common selector
            description_article = response.css('h2.synopsis::text').get()

        author = response.css('a[rel="author"]::text').get()
        tags = response.css('div.tags a::text').getall()

        # Use article page data if available, otherwise fallback to list page data from meta
        final_headline = headline_article.strip(
        ) if headline_article else response.meta.get("headline_list")
        final_description = description_article.strip(
        ) if description_article else response.meta.get("description_list")

        yield {
            "headline": final_headline,
            "description": final_description,
            "url": response.meta.get("url"),
            "last_updated": None,  # Or parse if available on article page
            "category": response.url.split('/')[3] if len(response.url.split('/')) > 3 else None,
            "image_url": response.meta.get("image_url"),
            "author": author,
            "published_date": response.meta.get("published_date"),
            "source": "indianexpress.com",
            "content": content if content else None,
            "tags": tags if tags else None,
        }
