#!/usr/bin/env python3
import os
import sys
from scrapy import cmdline

# Run just the spider
sys.argv = ['scrapy', 'crawl', 'bbcspider', '-s', 'LOG_LEVEL=INFO']
cmdline.execute()