# import scrapy


# class IndiaTVNewsSpider(scrapy.Spider):
#     name = "IndiaTVNewsSpider"
#     allowed_domains = ["www.indiatvnews.com"]

#     def start_requests(self):
#         for page_num in range(2, 26):
#             url = f"https://www.indiatvnews.com/india/{page_num}"
#             yield scrapy.Request(url, callback=self.parse)

#     def parse(self, response):
#         articles = response.xpath("//ul[@class='newsListfull']/li")

#         for article in articles:
#             headline = article.xpath(".//h3[@class='caption']/a/text()").get()
#             description = article.xpath(".//p[@class='artdesc']/text()").get()
#             url = article.xpath(".//h3[@class='caption']/a/@href").get()
#             published_date = article.xpath(
#                 ".//span[@class='deskTime']/text()").get()
#             image_url = article.xpath(".//a[@class='thumb']/img/@data-original").get() \
#                 or article.xpath(".//a[@class='thumb']/img/@src").get()

#             full_url = response.urljoin(url) if url else None

#             yield scrapy.Request(
#                 url=full_url,
#                 callback=self.parse_article,
#                 meta={
#                     "headline": headline.strip() if headline else None,
#                     "description": description.strip() if description else None,
#                     "url": full_url,
#                     "last_updated": published_date or None,
#                     "image_url": image_url or None,
#                 }
#             )

#     def parse_article(self, response):
#         content_paragraphs = response.xpath(
#             "//div[@id='content']//p/text()").getall()
#         content = " ".join([p.strip()
#                            for p in content_paragraphs if p.strip()])

#         yield {
#             "headline": response.meta["headline"],
#             "description": response.meta["description"],
#             "url": response.meta["url"],
#             "last_updated": response.meta["last_updated"],
#             "category": None,
#             "image_url": response.meta["image_url"],
#             "author": None,
#             "published_date": response.meta["last_updated"],
#             "source": "indiatvnews.com",
#             "content": content or None,
#             "tags": None,
#             "comments_count": None,
#             "shares_count": None,
#             "sentiment": None,
#             "bias_score": None
#         }
import scrapy


class IndiaTVNewsSpider(scrapy.Spider):
    name = "IndiaTVNewsSpider"
    allowed_domains = ["www.indiatvnews.com"]

    def start_requests(self):

        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        for page_num in range(2, 3):  # Start from page 1 up to 25
            url = f"https://www.indiatvnews.com/india/{page_num}"
            # For the first page, the URL might be different (e.g., without /1)
            # Indiatvnews seems to use /1, /2 etc. for pagination directly.
            # If page 1 is https://www.indiatvnews.com/india/, this loop is fine.
            # Let's assume the pattern holds for page 1 as well.
            if page_num == 1:
                # Or specific URL for first page if different
                url = "https://www.indiatvnews.com/india"
            yield scrapy.Request(url, callback=self.parse_headlines)

    def handle_error(self, failure):
        self.logger.error(
            f"Request failed: {failure.request.url}, Meta: {failure.request.meta}, Error: {failure.value}")

    def parse_headlines(self, response):
        # Using XPath based on headlines.html
        articles = response.xpath("//ul[@class='newsListfull']/li")

        for article in articles:
            # Extracting from the <a> tag directly under <li> for headline and URL
            headline = article.xpath("./a/@title").get()
            url = article.xpath("./a/@href").get()

            description = article.xpath(".//p[@class='artdesc']/text()").get()
            published_date = article.xpath(
                ".//span[@class='deskTime']/text()").get()

            # Image URL extraction - kept as is, as it might work on live site
            # headlines.html sample did not contain these image structures in the list.
            image_url = article.xpath(".//a[@class='thumb']/img/@data-original").get() \
                or article.xpath(".//a[@class='thumb']/img/@src").get()

            full_url = response.urljoin(url) if url else None

            if full_url:
                yield scrapy.Request(
                    url=full_url,
                    callback=self.parse_article,
                    meta={
                        "headline": headline.strip() if headline else None,
                        "description": description.strip() if description else None,
                        "url": full_url,
                        # Use this for both last_updated and published_date
                        "published_date": published_date.strip() if published_date else None,
                        "image_url": response.urljoin(image_url) if image_url else None,
                    },
                    errback=self.handle_error,
                    headers={
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                        'Accept-Language': 'en-US,en;q=0.9',
                    }
                )

    def parse_article(self, response):
        # Based on article.html
        content_paragraphs = response.xpath(
            "//div[@id='content']//p//text()").getall()  # Get all text nodes within p tags
        content = " ".join([p.strip()
                           for p in content_paragraphs if p.strip()])

        # Extracting tags based on article.html
        tags = response.xpath(
            "//div[contains(@class, 'tag')]/a/text()").getall()
        cleaned_tags = [tag.strip()
                        for tag in tags if tag.strip()] if tags else None

        # Extracting author - article.html doesn't show a clear author, defaulting to None
        # If author information is found in a consistent location, it can be added here.
        # For example, if it's in <meta name="author" content="Author Name">
        # author = response.xpath("//meta[@name='author']/@content").get()
        author = None  # Defaulting to None as per previous structure

        # Extracting category - article.html doesn't show a clear category
        # category = None # Defaulting to None

        yield {
            "headline": response.meta.get("headline"),
            "description": response.meta.get("description"),
            "url": response.meta.get("url"),
            # Using published_date from meta
            "last_updated": response.meta.get("published_date"),
            "category": None,  # Category not easily identifiable from article.html
            "image_url": response.meta.get("image_url"),
            "author": author,
            # Using published_date from meta
            "published_date": response.meta.get("published_date"),
            "source": "indiatvnews.com",
            "content": content if content else None,
            "tags": cleaned_tags,
            "comments_count": None,  # Not available in HTML
            "shares_count": None,  # Not available in HTML
            "sentiment": None,  # To be determined by other processes
            "bias_score": None  # To be determined by other processes
        }
