# -*- coding: utf-8 -*-
BOT_NAME = 'scraper'
SPIDER_MODULES = ['scraper.spiders']
NEWSPIDER_MODULE = 'scraper.spiders'
DOWNLOAD_DELAY = 0.25
ITEM_PIPELINES = {
   'scraper.pipelines.MultiJsonItemPipeline': 300,
}
