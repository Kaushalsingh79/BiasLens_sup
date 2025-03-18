import json
import scrapy


class BbcspiderSpider(scrapy.Spider):
    name = "BBCSpider"
    allowed_domains = ["web-cdn.api.bbci.co.uk"]

    def start_requests(self):
        # First request to fetch JSON data
        pageIter = 0
        while pageIter < 12:
            yield scrapy.Request(
                f"https://web-cdn.api.bbci.co.uk/xd/content-collection/1a3cd4db-fe3d-46f2-9c9a-927a01b00c91?country=in&page={pageIter}&size=9&path=%2Fnews%2Fworld%2Fasia%2Findia",
                callback=self.parse_json
            )

            pageIter += 1

    def parse_json(self, response):
        data = json.loads(response.text)
        for item in data.get("data", []):
            yield {
                "headline": item.get("title") or None,
                "description": item.get("summary") or None,
                "url": item.get("path") or None,
                "last_updated": item.get("lastPublishedAt") or None,
                "category": None,
                "image_url": item.get("indexImage", {}).get("model", {}).get("blocks", {}).get("src") or None,
                "author": None,
                "published_date": item.get("firstPublishedAt") or None,
                "source": "bbc.com",
                "content": None,
                "tags": item.get("topics") or None,
                "comments_count": None,
                "shares_count": None,
                "sentiment": None,
                "bias_score": None

            }


# TODO : add href to this
