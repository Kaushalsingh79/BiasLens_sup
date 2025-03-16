import scrapy


class IndianexpressspiderSpider(scrapy.Spider):
    name = "IndianExpressSpider"
    allowed_domains = ["indianexpress.com"]
    start_urls = ["https://indianexpress.com/section/india/?ref=l1_home"]

    def parse(self, response):
        pass
