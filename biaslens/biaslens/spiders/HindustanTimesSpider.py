import scrapy


class HindustantimesspiderSpider(scrapy.Spider):
    name = "HindustanTimesSpider"
    allowed_domains = ["www.hindustantimes.com"]
    start_urls = ["https://www.hindustantimes.com/india-news"]

    def parse(self, response):
        pass
