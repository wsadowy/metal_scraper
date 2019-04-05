# -*- coding: utf-8 -*-

import scrapy


class BandItem(scrapy.Item):
    metallum_id = scrapy.Field()
    name = scrapy.Field()
    country = scrapy.Field()
    location = scrapy.Field()
    status = scrapy.Field()
    founding_year = scrapy.Field()
    genre = scrapy.Field()
    lyrical_themes = scrapy.Field()
    current_label = scrapy.Field()
    releases = scrapy.Field()
    similar_artists = scrapy.Field()
    lineup = scrapy.Field()


class ReleaseItem(scrapy.Item):
    metallum_id = scrapy.Field()
    name = scrapy.Field()
    band = scrapy.Field()
    type = scrapy.Field()
    release_date = scrapy.Field()
    reviews_avg = scrapy.Field()
    reviews_count = scrapy.Field()
    lineup = scrapy.Field()
    label = scrapy.Field()


class LabelItem(scrapy.Item):
    metallum_id = scrapy.Field()
    name = scrapy.Field()
    country = scrapy.Field()
    status = scrapy.Field()
    specialized_in = scrapy.Field()
    founding_year = scrapy.Field()
    current_bands = scrapy.Field()
    past_bands = scrapy.Field()
    releases = scrapy.Field()


class CountryItem(scrapy.Item):
    metallum_id = scrapy.Field()
    name = scrapy.Field()
    bands = scrapy.Field()


class MemberItem(scrapy.Item):
    metallum_id = scrapy.Field()
    name = scrapy.Field()
    bands = scrapy.Field()
