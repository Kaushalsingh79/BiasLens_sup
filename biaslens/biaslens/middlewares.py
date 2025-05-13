# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

import random
from scrapy import signals

# useful for handling different item types with a single interface
from itemadapter import is_item, ItemAdapter


class BiaslensSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class BiaslensDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


# filepath: c:\Users\1100a\Documents\BiasLens\biaslens\biaslens\middlewares.py


class CustomProxyMiddleware(object):
    def __init__(self, settings):
        # You should populate this list with your proxies
        # Format: 'http://ip:port' or 'http://user:password@ip:port'
        self.proxies = settings.getlist('PROXY_LIST')
        if not self.proxies:
            # You can raise an error or log a warning if no proxies are provided
            print("Warning: PROXY_LIST is empty in settings.py. No proxies will be used.")

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def process_request(self, request, spider):
        if not self.proxies:
            return  # Don't set proxy if list is empty

        # Don't PProxy if 'dont_proxy' is set in request.meta
        if request.meta.get('dont_proxy'):
            return

        proxy = random.choice(self.proxies)
        request.meta['proxy'] = proxy
        spider.logger.debug(f"Using proxy: {proxy} for request: {request.url}")

    def process_exception(self, request, exception, spider):
        # Handle proxy errors if needed, e.g., try another proxy
        proxy = request.meta.get('proxy')
        spider.logger.warning(
            f"Proxy {proxy} failed for {request.url} with exception: {exception}")
        # You could implement logic here to ban a failing proxy or retry with a new one
        # For simplicity, we'll just let Scrapy handle the retry with a potentially new proxy on the next attempt
        return None  # Return None to let Scrapy's default exception handling take over
