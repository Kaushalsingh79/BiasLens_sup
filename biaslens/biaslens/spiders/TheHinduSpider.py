import scrapy


class ThehinduspiderSpider(scrapy.Spider):
    name = "TheHinduSpider"
    allowed_domains = ["www.thehindu.com"]
    start_urls = ["https://www.thehindu.com/news/national/"]

    def parse(self, response):
        pass
