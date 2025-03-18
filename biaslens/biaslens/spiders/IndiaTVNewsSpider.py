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

            yield {
                "headline": headline.strip() if headline else None,
                "description": description.strip() if description else None,
                "url": response.urljoin(url) if url else None,
                "last_updated": published_date or None,
                "category": None,
                "image_url": image_url or None,
                "author": None,
                "published_date": published_date or None,
                "source": "indiatvnews.com",
                "content": None,
                "tags": None,
                "comments_count": None,
                "shares_count": None,
                "sentiment": None,
                "bias_score": None
            }
