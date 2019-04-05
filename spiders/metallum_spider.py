# -*- coding: UTF-8 -*-

import json
import re
from os import path

import scrapy
from lxml import etree

from items import (BandItem, CountryItem, LabelItem, MemberItem,
                           ReleaseItem)
from utils import increment_paginated_url


class MetallumSpider(scrapy.Spider):

    name = 'metallum_spider'
    main_site = 'https://www.metal-archives.com'
    allowed_domains = ['metal-archives.com']
    start_urls = [
        path.join(main_site, 'browse/letter'),
    ]

    def parse(self, response):
        ul = response.xpath('/html/body/div/div[3]/div[1]/ul/li')
        for li in ul:
            yield scrapy.Request(li.xpath('a/@href').get(), callback=self.parse_letter)

    def parse_letter(self, response):
        letter = response.url.split('/')[-1]
        page_url = 'browse/ajax-letter/l/{}/json/1?sEcho=2&iColumns=4&sColumns=&iDisplayStart=0'.format(letter)
        yield scrapy.Request(path.join(self.main_site,
                                       page_url.format(letter)),
                             callback=self.parse_page,
                             meta={"page_url": page_url, "letter": letter})

    def parse_page(self, response):
        json_data = json.loads(response.body_as_unicode())
        bands_list = json_data['aaData']
        if not bands_list:
            return
        for band_data in bands_list:
            band = band_data[0].replace("&", "&amp;")
            band_url = etree.fromstring(band).xpath('@href')[0]
            yield scrapy.Request(band_url, callback=self.parse_band)
        yield scrapy.Request(increment_paginated_url(response.url),
                             callback=self.parse_page)

    def populate(self, response, item, main_attrib, type_node_xpath, rows_xpath, disallowed_ids=None):
        rows = response.xpath(rows_xpath)
        for row in rows:
            type_parent_node_id = row.xpath(type_node_xpath).get()
            _type = type_parent_node_id.split('_')[-1].strip()
            if disallowed_ids and type_parent_node_id in disallowed_ids:
                continue
            if _type not in item[main_attrib]:
                item[main_attrib][_type] = []
            if main_attrib == 'lineup':
                yield from self._populate_lineup(row, item, _type)
            elif main_attrib == 'bands':
                yield from self._populate_member_bands(row, item, _type)

    def _populate_lineup(self, row, item, type_attrib):
        url_data = row.xpath('td[1]/a')
        url = url_data.xpath('@href').get()
        metallum_id = url.split('/')[-1]
        roles = [e.strip() for e in row.xpath('td[2]/text()').get().split(',')]
        item['lineup'][type_attrib].append(
            {
                'metallum_id': metallum_id,
                'name': url_data.xpath('text()').get(),
                'roles': roles
            }
        )
        yield scrapy.Request(url, self.parse_member, meta={"id": metallum_id})

    @staticmethod
    def _get_roles(album_rows, band_roles_info, roles_total):
        roles_regex = r'[\d+a-z A-Z]+(( [\w+]+)|([\w+]+))(?![^(]*\))'
        if album_rows:
            for row in album_rows:
                album_roles_info = row.xpath('td[3]/text()').get()
                found = re.finditer(roles_regex, album_roles_info)
                for f in found:
                    roles_total.add(f.group().strip())
        elif band_roles_info:
            found = re.finditer(roles_regex, band_roles_info)
            for f in found:
                roles_total.add(f.group().strip())

    def _populate_member_bands(self, row, item, type_attrib):
        row_id = row.xpath('@id').get()
        try:
            url_section = row.xpath('h3/a')
            band_id = re.match(r'memberInBand_(\d+)', row_id).group(1)
            band_name = url_section.xpath('text()').get().strip()
        except AttributeError:
            band_id = "N/A"
            band_name = row.xpath('h3/text()').get().strip()
        roles_total = set()
        album_rows = row.xpath('table/tr')
        band_roles_info = row.xpath('p/strong/text()').get()
        self._get_roles(album_rows, band_roles_info, roles_total)
        item['bands'][type_attrib].append(
            {
                'metallum_id': band_id,
                'name': band_name,
                'roles': roles_total,
            }
        )
        yield

    def parse_member(self, response):
        _id = response.meta['id']
        member_item = MemberItem()
        member_info = response.xpath('//*[@id="member_info"]')
        member_item['metallum_id'] = _id
        member_item['name'] = member_info.xpath('*[@class="float_left"]/dd[1]/text()').get().strip()
        member_item['bands'] = {}
        yield from self.populate(response,
                                 member_item,
                                 'bands',
                                 '../../@id',
                                 '//div[contains(@id, "memberInBand_")]')
        yield member_item

    def parse_band(self, response):
        band_item = BandItem()
        band_info = response.xpath('//*[@id="band_info"]')
        band_stats = band_info.xpath('*[@id="band_stats"]')
        left_stats = band_stats.xpath('*[@class="float_left"]')
        right_stats = band_stats.xpath('*[@class="float_right"]')
        band_item['name'] = band_info.xpath('h1/a/text()').get()
        band_item['metallum_id'] = band_info.xpath('h1/a/@href').get().split('/')[-1]
        band_item['location'] = left_stats.xpath('dd[2]/text()').get()
        band_item['status'] = left_stats.xpath('dd[3]/text()').get()
        band_item['founding_year'] = left_stats.xpath('dd[4]/text()').get()
        band_item['genre'] = right_stats.xpath('dd[1]/text()').get()
        band_item['lyrical_themes'] = right_stats.xpath('dd[2]/text()').get()
        band_item['releases'] = []
        band_item['similar_artists'] = []
        band_item['lineup'] = {}
        country_section = left_stats.xpath('dd[1]/a')
        country_url = country_section.xpath('@href').get()
        country_name = country_section.xpath('text()').get()
        country_id = country_url.split('/')[-1]
        band_item['country'] = {
            'name': country_name,
            'metallum_id': country_id,
        }
        label_section = right_stats.xpath('dd[3]')
        label_url = label_section.xpath('a/@href').get()
        label_id = label_url.split('/')[-1] if label_url else None
        label_name = label_section.xpath('a/text()').get() if label_url else None
        band_item['current_label'] = {
            'name': label_name,
            'metallum_id': label_id,
        }

        yield from self.populate(response, band_item,
                                 'lineup',
                                 '../../../@id',
                                 '//table/tr[@class="lineupRow"]',
                                 disallowed_ids=['band_tab_members_all'])

        if label_url:
            yield scrapy.Request(label_url,
                                 callback=self.parse_label,
                                 meta={"metallum_id": label_id, "name": label_name}
                                 )

        yield scrapy.Request(country_url,
                             callback=self.parse_country,
                             meta={"metallum_id": country_id, "name": country_name})

        releases_url = path.join(self.main_site, f'band/discography/id/'
                                                 f'{band_item["metallum_id"]}/tab/all')
        yield scrapy.Request(releases_url,
                             callback=self.parse_releases,
                             meta={"band_item": band_item},
                             )

    def parse_country(self, response):
        name = response.meta["name"]
        metallum_id = response.meta["metallum_id"]
        country_item = CountryItem()
        country_item["name"] = name
        country_item["metallum_id"] = metallum_id
        country_item["bands"] = []
        yield scrapy.Request(path.join(self.main_site, f'browse/ajax-country/c/{metallum_id}'
                                                       f'/json/1?sEcho=3&iColumns=4&sColumns=&iDisplayStart=0'),
                             callback=self.parse_country_bands,
                             meta={"country_item": country_item})

    def parse_country_bands(self, response):
        country_item = response.meta["country_item"]
        json_data = json.loads(response.body_as_unicode())
        bands_list = json_data['aaData']
        if not bands_list:
            yield country_item
        else:
            yield from self._populate_o2m_field_str(bands_list, country_item, "bands")
            yield scrapy.Request(increment_paginated_url(response.url),
                                 callback=self.parse_country_bands,
                                 meta={"country_item": country_item})

    @staticmethod
    def _populate_o2m_field_str(lst, item, field, follow=False, callback=None):
        for data in lst:
            elem_str = data[0].replace("&", "&amp;")
            elem = etree.fromstring(elem_str)
            url = elem.xpath('@href')[0]
            item[field].append({
                "metallum_id": url.split('/')[-1],
                "name": elem.xpath('text()')[0],
            })
            if follow:
                yield scrapy.Request(url, callback=callback)
        yield item

    def parse_label(self, response):
        label_item = LabelItem()
        right_stats = response.xpath('//*[@id="label_info"]/dl[2]')
        label_item['metallum_id'] = response.meta['metallum_id']
        label_item['name'] = response.meta['name']
        label_item['country'] = {
            'name': label_item['name'],
            'metallum_id': label_item['metallum_id'],
        }
        label_item['status'] = right_stats.xpath('dd[1]/span/text()').get()
        label_item['specialized_in'] = right_stats.xpath('dd[2]/text()').get()
        label_item['founding_year'] = right_stats.xpath('dd[3]/text()').get()
        label_item['current_bands'] = []
        label_item['past_bands'] = []
        label_item['releases'] = []
        past_bands_slug = 'ajax-bands-past'
        bands_url = path.join(self.main_site, f'label/{past_bands_slug}/nbrPerPage/100000000/id/'
                                              f'{label_item["metallum_id"]}?sEcho=4&iColumns=3&sColumns=')
        yield scrapy.Request(bands_url,
                             callback=self.parse_label_bands,
                             meta={"label_item": label_item,
                                   "bands_type": past_bands_slug})

    def parse_label_bands(self, response):
        bands_type = response.meta["bands_type"]
        label_item = response.meta["label_item"]
        json_data = json.loads(response.body_as_unicode())
        past_bands_slug = "ajax-bands-past"
        current_bands_slug = "ajax-bands"

        bands_type_mapping = {
            current_bands_slug: "current_bands",
            past_bands_slug: "past_bands",
        }

        which_bands = bands_type_mapping[bands_type]

        yield from self._populate_o2m_field_str(json_data["aaData"], label_item, which_bands)

        new_response_url = response.url.replace(past_bands_slug, current_bands_slug)
        if response.url != new_response_url:
            return scrapy.Request(new_response_url,
                                  callback=self.parse_label_bands,
                                  meta={"label_item": label_item,
                                        "bands_type": current_bands_slug})
        return label_item

    def parse_releases(self, response):
        band_item = response.meta["band_item"]
        for row in response.xpath('/html/body/table/tbody/tr'):
            release_name = row.xpath('td[1]/a/text()').get()
            release_url = row.xpath('td[1]/a/@href').get()
            if not release_url:
                return
            release_id = release_url.split('/')[-1]
            band_item["releases"].append({
                "name": release_name,
                "metallum_id": release_id,
            })
            release_item = ReleaseItem()
            release_item["metallum_id"] = release_id
            release_item["name"] = release_name
            release_item["band"] = band_item["metallum_id"]
            release_item["type"] = row.xpath('td[2]/text()').get()
            release_item["release_date"] = row.xpath('td[3]/text()').get()
            reviews_string = row.xpath('td[4]/a/text()').get()
            reviews_regex = r'(\d+) \((\d+)%\)'
            cnt = re.search(reviews_regex, reviews_string).group(1).strip() if reviews_string else ''
            avg = re.search(reviews_regex, reviews_string).group(2).strip() if reviews_string else ''
            release_item["reviews_avg"] = avg
            release_item["reviews_count"] = cnt
            release_item["lineup"] = {}
            yield scrapy.Request(release_url, callback=self.parse_release,
                                 meta={"release_item": release_item})
        recommendations_url = path.join(self.main_site, f'band/ajax-recommendations/id/'
                                                        f'{band_item["metallum_id"]}')
        yield scrapy.Request(recommendations_url,
                             callback=self.parse_recommendations,
                             meta={"band_item": band_item})

    def parse_release(self, response):
        release_item = response.meta["release_item"]
        label_section = response.xpath('//*[@id="album_info"]/dl[2]/dd[1]')
        label_url = label_section.xpath('a/@href').get()
        label_id_section = label_url.split('/')[-1] if label_url else None
        label_id = re.search(r'(\d+)', label_id_section).group(1) if label_url else None
        label_name = label_section.xpath('a/text()').get() if label_url else None
        release_item["label"] = {
            'metallum_id': label_id,
            'name': label_name,
        }
        yield from self.populate(response,
                                 release_item,
                                 'lineup',
                                 '../../../@id',
                                 '//table/tr[@class="lineupRow"]', disallowed_ids=['album_all_members_lineup'])
        yield release_item

    def parse_recommendations(self, response):
        band_item = response.meta["band_item"]
        rows = response.xpath('/html/body/div[2]/table/tbody/tr')
        last_row = rows[-1]
        last_row_text = last_row.xpath('td/a/text()').get()
        last_row_id = last_row.xpath('td/@id').get()
        if last_row_id == "no_artists" or last_row_text == "show top 20 only":
            rows.pop()
        elif last_row_text == "see more":
            return scrapy.Request(response.urljoin('?showMoreSimilar=1'),
                                  callback=self.parse_recommendations,
                                  meta={"band_item": band_item})
        for row in rows:
            band_data = row.xpath('td[1]/a')
            band_name = band_data.xpath('text()').get()
            band_id = band_data.xpath('@href').get().split("/")[-1]
            band_item["similar_artists"].append({
                "name": band_name,
                "metallum_id": band_id,
            })
        return band_item
