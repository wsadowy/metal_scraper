# -*- coding: utf-8 -*-

from scrapy import signals
from scrapy.exporters import JsonItemExporter
from scrapy.xlib.pydispatch import dispatcher


def item_type(item):
    return type(item).__name__.replace('Item', '').lower()


class MultiJsonItemPipeline(object):
    save_types = ['band', 'release', 'label', 'country', 'member']

    def __init__(self):
        self.files = {}
        self.exporters = {}
        dispatcher.connect(self.spider_opened, signal=signals.spider_opened)
        dispatcher.connect(self.spider_closed, signal=signals.spider_closed)

    def spider_opened(self, spider):
        self.files = {name: open(f'{name}.json', 'wb') for name in self.save_types}
        self.exporters = {name: JsonItemExporter(self.files[name], indent=4, ensure_ascii=False)
                          for name in self.save_types}
        [e.start_exporting() for e in self.exporters.values()]

    def spider_closed(self, spider):
        [e.finish_exporting() for e in self.exporters.values()]
        [f.close() for f in self.files.values()]

    def process_item(self, item, spider):
        itype = item_type(item)
        if itype in set(self.save_types):
            self.exporters[itype].export_item(item)
        return item


class ScraperPipeline(object):
    def process_item(self, item, spider):
        return item
