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
                "title": title.strip() if title else "",
                "summary": "",
                "topics": [],
                "image_url": "",
                "first_published": "",
                "last_published": "",
                "url": response.urljoin(link) if link else "",
            }
