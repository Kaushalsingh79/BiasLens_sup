import scrapy


class TimesOfIndiaSpider(scrapy.Spider):
    name = "TimesOfIndiaSpider"
    allowed_domains = ["timesofindia.indiatimes.com"]

    def start_requests(self):
        for page_num in range(2, 26):
            url = f"https://timesofindia.indiatimes.com/india/{page_num}"
            yield scrapy.Request(url, callback=self.parse_page)

    def parse_page(self, response):
        articles = response.xpath("//ul[@class='list5 clearfix']/li")
        for article in articles:
            title = article.xpath(".//span[@class='w_tle']/a/text()").get()
            link = article.xpath(".//span[@class='w_tle']/a/@href").get()

            yield {
                "headline": title.strip() if title else None,
                "description": None,
                "url": response.urljoin(link) if link else None,
                "last_updated": None,
                "category": None,
                "image_url": None,
                "author": None,
                "published_date": None,
                "source": "timesofindia.indiatimes.com",
                "content": None,
                "tags": None,
                "comments_count": None,
                "shares_count": None,
                "sentiment": None,
                "bias_score": None
            }
