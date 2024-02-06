from datetime import datetime
from urllib.parse import urlparse

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
            is_valid_meeting = self._check_valid_meeting(item)
            if not is_valid_meeting:
                continue
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

    def _check_valid_meeting(self, item):
        """Second column may contain a link that reads "In Progress" if the
        meeting is underway. This row doesn't contain valid data.
        """
        in_progress_el = item.css("tr td:nth-child(2) a::text").get()
        if in_progress_el and "in progress" in in_progress_el.lower():
            return False
        return True

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
            valid_href = self._normalize_url(href)
            links.append({"href": valid_href, "title": title})
        return links

    def _parse_source(self, response):
        return response.url

    def _normalize_url(self, url):
        """
        Normalize a URL based on its initial character(s). Handles cases where the URL
        starts with "//", "/", or is a full URL.
        """
        parsed_start_url = urlparse(self.start_urls[0])
        if url.startswith("//"):
            # Prepend the protocol of start_url
            normalized_url = f"{parsed_start_url.scheme}:{url}"
        elif url.startswith("/"):
            # Prepend the protocol and domain of start_url
            base_url = f"{parsed_start_url.scheme}://{parsed_start_url.netloc}"
            normalized_url = f"{base_url}{url}"
        else:
            # URL does not match the specified cases, return as is
            normalized_url = url
        return normalized_url
