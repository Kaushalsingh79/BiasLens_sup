import json
import scrapy


class BbcspiderSpider(scrapy.Spider):
    name = "BBCSpider"
    allowed_domains = ["web-cdn.api.bbci.co.uk",
                       "bbc.com"]  # Add bbc.com domain

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
            article_url = item.get("path")
            if article_url:
                # Follow the article URL to fetch content
                full_url = f"https://www.bbc.com{article_url}"
                yield scrapy.Request(
                    full_url,
                    callback=self.parse_article_content,
                    meta={
                        'item': {
                            "headline": item.get("title") or None,
                            "description": item.get("summary") or None,
                            "url": article_url,
                            "last_updated": item.get("lastPublishedAt") or None,
                            "category": None,
                            "image_url": item.get("indexImage", {}).get("model", {}).get("blocks", {}).get("src") or None,
                            "author": None,
                            "published_date": item.get("firstPublishedAt") or None,
                            "source": "bbc.com",
                            "tags": item.get("topics") or None,
                            "comments_count": None,
                            "shares_count": None,
                            "sentiment": None,
                            "bias_score": None,
                        }
                    }
                )
            else:
                yield {
                    "headline": item.get("title") or None,
                    "description": item.get("summary") or None,
                    "url": article_url,
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
                    "bias_score": None,
                }

    def parse_article_content(self, response):
        """
        Parse the content from the article page.
        Extracts content from paragraph tags in the text-block components.
        """
        item = response.meta['item']

        # Use a better CSS selector to extract just the text from paragraphs
        paragraph_texts = []

        # Try several selectors to get the paragraph text
        text_blocks = response.css(
            'div[data-component="text-block"] p::text').getall()
        if text_blocks:
            paragraph_texts.extend(text_blocks)

        # Try alternative selectors if needed
        if not paragraph_texts:
            paragraph_texts = response.css('article p::text').getall()

        if not paragraph_texts:
            paragraph_texts = response.css(
                'div.ssrcss-uf6wea-RichTextComponentWrapper p::text').getall()

        # For complicated HTML, we might need to get the text from each paragraph
        if not paragraph_texts:
            for paragraph in response.css('div[data-component="text-block"] p'):
                paragraph_text = paragraph.css('::text').get()
                if paragraph_text:
                    paragraph_texts.append(paragraph_text.strip())

        # Join all paragraphs into a single content string
        content = '\n'.join([p.strip() for p in paragraph_texts if p.strip()])

        # Try to extract the author
        author = response.css(
            'div[data-component="byline-block"] span::text').get()
        if author:
            item['author'] = author.strip()

        # Try to extract category
        category_elements = response.css(
            'a[data-testid="internal-link"]::text')
        if category_elements and len(category_elements) > 0:
            item['category'] = category_elements[0].get().strip()

        # Set the content
        item['content'] = content

        # If content is still empty, use a more robust method
        if not content:
            # Use a fallback method to extract all visible text
            visible_texts = response.xpath('//p/text()').getall()
            content = '\n'.join([t.strip()
                                for t in visible_texts if t.strip()])
            item['content'] = content

        # Yield the item instead of returning it for Scrapy to process
        yield item


# TODO : add href to this
