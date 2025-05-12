import scrapy
import re  # Added import


class TimesOfIndiaSpider(scrapy.Spider):
    name = "TimesOfIndiaSpider"
    allowed_domains = ["timesofindia.indiatimes.com"]

    def start_requests(self):
        # The original spider iterated from page 2 to 25.
        for page_num in range(2, 26):  # Pages 2 to 25
            url = f"https://timesofindia.indiatimes.com/india/{page_num}"
            yield scrapy.Request(url, callback=self.parse_page)

    def parse_page(self, response):
        # XPath for article links on the listing page (as in original spider)
        articles = response.xpath("//ul[@class='list5 clearfix']/li")
        for article in articles:
            link = article.xpath(".//span[@class='w_tle']/a/@href").get()
            if link:
                article_url = response.urljoin(link)
                # Instead of parsing here, go to a method that will try to get the print version
                yield scrapy.Request(article_url, callback=self.transform_to_print_request)

    def transform_to_print_request(self, response):
        """
        Receives the response from the main article page,
        constructs the URL for its print version, and requests it.
        """
        original_url = response.url

        # Extract article ID from URL like /articleshow/12345.cms or /articleshow_new/12345.cms
        # The print link is typically /articleshowprint/ARTICLE_ID.cms
        match = re.search(
            r'/(?:articleshow|articleshow_new)/(\d+)\.cms', original_url)
        if match:
            article_id = match.group(1)
            # Construct the print URL path. Example: /articleshowprint/121107537.cms
            print_url_path = f"/articleshowprint/{article_id}.cms"
            print_url = response.urljoin(print_url_path)

            self.logger.info(
                f"Requesting print version: {print_url} from original: {original_url}")
            yield scrapy.Request(
                print_url,
                callback=self.parse_print_article,
                # Pass original URL for the final item
                meta={'original_url': original_url}
            )
        else:
            self.logger.warning(
                f"Could not extract article ID to form print URL from: {original_url}. Skipping print version for this article.")
            # If you wanted a fallback to parse the main page, you could add it here.
            # For now, we only proceed if we can get to the print page.

    def parse_print_article(self, response):
        """
        Parses the content from the print version of the article.
        The HTML structure and XPaths are based on the user-provided snippet for the print page.
        """
        original_url = response.meta.get(
            'original_url', response.url)  # Retrieve the original URL

        # Headline from: <h1 data-articletitle="" class="heading1">...</h1> in <section class="title_section ...">
        title = response.xpath(
            "//section[contains(@class, 'title_section')]//h1[@data-articletitle]/text()").get()
        if not title:  # Fallback if data-articletitle attribute is not present but h1 is
            title = response.xpath(
                "//section[contains(@class, 'title_section')]//h1/text()").get()

        # Author and Published Date from: <div class="time_cptn">TIMESOFINDIA.COM | May 12, 2025, 06.48 PM IST</div>
        time_caption_text = response.xpath(
            "//div[@class='time_cptn']/text()").get()

        author = None
        published_date_str = None

        if time_caption_text:
            try:
                # Split "AUTHOR | DATE"
                parts = [p.strip()
                         for p in time_caption_text.strip().split('|', 1)]
                if len(parts) == 2:
                    author = parts[0]
                    published_date_str = parts[1]
                elif len(parts) == 1:  # Only one part found, could be author or date
                    # Heuristic: if it contains a year and AM/PM/IST, assume it's a date
                    if re.search(r'\d{4}', parts[0]) and re.search(r'(AM|PM|IST)', parts[0], re.IGNORECASE):
                        published_date_str = parts[0]
                        # Default author if only date is found
                        author = "TIMESOFINDIA.COM"
                    else:  # Assume it's an author
                        author = parts[0]
            except Exception as e:
                self.logger.warning(
                    f"Could not parse author/date from '{time_caption_text}' on {response.url}: {e}")

        # Default author if still None or empty after parsing attempts
        if not author:
            author = "TIMESOFINDIA.COM"  # Default author

        # Content from: <arttextxml><div class="section1"><div class="Normal">...</div></div></arttextxml>
        paragraphs = response.xpath(
            "//arttextxml//div[contains(@class, 'Normal')]//text()[not(ancestor::script) and not(ancestor::style)]"
        ).getall()
        content = ' '.join([p.strip() for p in paragraphs if p.strip()])

        # Image URL from print page snippet: <img class="articlevideo_pic" src="/thumb/msid-121107577..."
        # This is likely a video thumbnail. Make it absolute.
        image_url_relative = response.xpath(
            "//img[contains(@class, 'articlevideo_pic')]/@src").get()
        image_url = response.urljoin(
            image_url_relative) if image_url_relative else None

        yield {
            "headline": title.strip() if title else None,
            "description": None,  # Not available in the print view snippet provided
            "url": original_url,  # Use the original article URL
            # Using published_date as last_updated for now
            "last_updated": published_date_str,
            "category": None,  # Not available from print view snippet
            "image_url": image_url,
            "author": author.strip() if author else None,  # Ensure author is stripped
            "published_date": published_date_str,
            "source": "timesofindia.indiatimes.com",  # Source domain
            "content": content if content else None,
            "tags": None,  # Not available from print view snippet
            "comments_count": None,  # Not available
            "shares_count": None,  # Not available
            "sentiment": None,  # Not applicable for scraping
            "bias_score": None  # Not applicable for scraping
        }
