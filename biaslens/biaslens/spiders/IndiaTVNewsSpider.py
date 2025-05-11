import scrapy


class IndiaTVNewsSpider(scrapy.Spider):
    name = "IndiaTVNewsSpider"
    allowed_domains = ["www.indiatvnews.com"]

    def start_requests(self):
        for page_num in range(2, 26):
            url = f"https://www.indiatvnews.com/india/{page_num}"
            yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        articles = response.xpath("//ul[@class='newsListfull']/li")

        for article in articles:
            headline = article.xpath(".//h3[@class='caption']/a/text()").get()
            description = article.xpath(".//p[@class='artdesc']/text()").get()
            url = article.xpath(".//h3[@class='caption']/a/@href").get()
            published_date = article.xpath(
                ".//span[@class='deskTime']/text()").get()
            image_url = article.xpath(".//a[@class='thumb']/img/@data-original").get() \
                or article.xpath(".//a[@class='thumb']/img/@src").get()

            full_url = response.urljoin(url) if url else None

            yield scrapy.Request(
                url=full_url,
                callback=self.parse_article,
                meta={
                    "headline": headline.strip() if headline else None,
                    "description": description.strip() if description else None,
                    "url": full_url,
                    "last_updated": published_date or None,
                    "image_url": image_url or None,
                }
            )

    def parse_article(self, response):
        content_paragraphs = response.xpath(
            "//div[@id='content']//p/text()").getall()
        content = " ".join([p.strip()
                           for p in content_paragraphs if p.strip()])

        yield {
            "headline": response.meta["headline"],
            "description": response.meta["description"],
            "url": response.meta["url"],
            "last_updated": response.meta["last_updated"],
            "category": None,
            "image_url": response.meta["image_url"],
            "author": None,
            "published_date": response.meta["last_updated"],
            "source": "indiatvnews.com",
            "content": content or None,
            "tags": None,
            "comments_count": None,
            "shares_count": None,
            "sentiment": None,
            "bias_score": None
        }
