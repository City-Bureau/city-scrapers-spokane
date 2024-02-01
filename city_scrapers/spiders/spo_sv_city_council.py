from datetime import datetime

import pytz
from city_scrapers_core.constants import (
    CITY_COUNCIL,
    COMMISSION,
    COMMITTEE,
    NOT_CLASSIFIED,
)
from city_scrapers_core.items import Meeting
from city_scrapers_core.spiders import CityScrapersSpider


class SvCityCouncilSpider(CityScrapersSpider):
    name = "spo_sv_city_council"
    agency = "Spokane Valley City Council"
    timezone = "America/Los_Angeles"
    start_urls = ["https://spokanevalley.granicus.com/ViewPublisher.php?view_id=3"]
    custom_settings = {"ROBOTSTXT_OBEY": False}
    location = {
        "name": "City Hall",
        "address": "10210 E Sprague Ave, Spokane Valley, WA 99206",
    }

    def parse(self, response):
        """
        `parse` should always `yield` Meeting items.

        Change the `_parse_title`, `_parse_start`, etc methods to fit your scraping
        needs.
        """
        meetings_table = response.css(
            "div#GranicusMainViewContent > div#upcoming > table > tbody"
        )
        for item in meetings_table.css("tr"):
            title = self._parse_title(item)
            meeting = Meeting(
                title=title,
                description="",
                classification=self._parse_classification(title),
                start=self._parse_start(item),
                end=None,
                all_day=False,
                time_notes=None,
                location=self.location,
                links=self._parse_links(item),
                source=self._parse_source(response),
            )
            meeting["status"] = self._get_status(meeting)
            meeting["id"] = self._get_id(meeting)
            yield meeting

    def _parse_title(self, item):
        """Parse meeting title."""
        return item.css('tr td[headers="EventName"]::text').get().strip()

    def _parse_classification(self, title):
        """Parses classification from allowed options."""
        lower_title = title.lower()
        if "commission" in lower_title:
            return COMMISSION
        elif "council" in lower_title:
            return CITY_COUNCIL
        elif "committee" in lower_title:
            return COMMITTEE
        return NOT_CLASSIFIED

    def _parse_start(self, item):
        unix_timestamp_str = item.css('tr td[headers*="EventDate"] span::text').get()
        unix_timestamp = int(unix_timestamp_str)

        # Create a timezone-aware datetime object in UTC
        start_utc = datetime.utcfromtimestamp(unix_timestamp).replace(tzinfo=pytz.utc)

        # Convert the UTC datetime to America/Los_Angeles time.
        pacific_tz = pytz.timezone(self.timezone)
        start_pacific = start_utc.astimezone(pacific_tz)

        # Convert to a timezone-naive datetime object as expected by CityScrapersSpider
        start_naive = start_pacific.replace(tzinfo=None)
        return start_naive

    def _parse_links(self, item):
        """Parse or generate links."""
        a_tags = item.css("tr a")
        links = []
        for a in a_tags:
            href = a.css("::attr(href)").get()
            title = a.css("::text").get()
            links.append({"href": href, "title": title})
        return links

    def _parse_source(self, response):
        return response.url
