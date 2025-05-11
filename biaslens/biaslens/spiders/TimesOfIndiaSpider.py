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
            link = article.xpath(".//span[@class='w_tle']/a/@href").get()
            if link:
                url = response.urljoin(link)
                yield scrapy.Request(url, callback=self.parse_article)

    def parse_article(self, response):
        title = response.xpath("//h1/text()").get()
        paragraphs = response.xpath(
            "//div[@data-articlebody='1']//text()").getall()
        content = ' '.join([p.strip() for p in paragraphs if p.strip()])
        image_url = response.xpath(
            "//div[@data-articlebody='1']//img/@src").get()

        yield {
            "headline": title.strip() if title else None,
            "description": None,
            "url": response.url,
            "last_updated": None,
            "category": None,
            "image_url": image_url,
            "author": None,
            "published_date": None,
            "source": "timesofindia.indiatimes.com",
            "content": content if content else None,
            "tags": None,
            "comments_count": None,
            "shares_count": None,
            "sentiment": None,
            "bias_score": None
        }
