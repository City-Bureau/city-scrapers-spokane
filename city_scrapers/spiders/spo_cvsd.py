import random
import re
from datetime import datetime

from bs4 import BeautifulSoup
from city_scrapers_core.constants import BOARD, NOT_CLASSIFIED
from city_scrapers_core.items import Meeting
from city_scrapers_core.spiders import CityScrapersSpider
from dateutil.relativedelta import relativedelta
from scrapy.http import Request


class SpokSvsdSpider(CityScrapersSpider):
    name = "spo_cvsd"
    agency = "Central Valley School District"
    timezone = "America/Los_Angeles"
    boarddocs_slug = "cvsd"
    boarddocs_committee_id = "A9XKGY51E05B"
    custom_settings = {"ROBOTSTXT_OBEY": False}
    location = {
        "name": "Learning and Teaching Center",
        "address": "2218 N Molter Rd Liberty Lake WA",
    }
    meeting_materials = {
        "href": "https://www.cvsd.org/apps/pages/BoardBulletin",
        "title": "Meeting materials",
    }

    def start_requests(self):
        """
        The start URL is a POST request to the BoardDocs API to get
        the list of meetings. The random int query param is not strictly
        necessary but it's included in the URL when navigating the boarddocs
        website and is likely used for cache-busting. While cache-busting
        is not necessary in our spider, we include the param so we can more
        closely mimic the behavior of a real user and reduce the risk of rate
        limiting.
        """
        return [
            Request(
                f"https://go.boarddocs.com/wa/{self.boarddocs_slug}/Board.nsf/BD-GetMeetingsList?open&0.{self.gen_random_int()}",  # noqa
                method="POST",
                body=f"current_committee_id={self.boarddocs_committee_id}",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        ]

    def parse(self, response):
        """Parse the JSON list of meetings"""
        meetings = response.json()
        filtered_meetings = self._get_clean_meetings(meetings)
        for item in filtered_meetings:
            meeting_id = item["unique"]
            start_date = item["start_date"]
            detail_url = f"https://go.boarddocs.com/wa/{self.boarddocs_slug}/Board.nsf/BD-GetMeeting?open&0.{self.gen_random_int()}"  # noqa
            details_body = (
                f"current_committee_id={self.boarddocs_committee_id}&id={meeting_id}"
            )
            yield Request(
                detail_url,
                method="POST",
                callback=self._parse_detail,
                meta={"start_date": start_date, "meeting_id": meeting_id},
                body=details_body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

    def _get_clean_meetings(self, data):
        """
        Cleans the data by removing any items with a date older than 2 months.
        Also adds a start_date key to each item with the parsed date.
        """
        today = datetime.today()
        two_months_ago = today - relativedelta(months=2)

        # Filter the data and add start_date
        filtered_data = []
        for item in data:
            if not item:
                # Some items are empty
                continue
            item_date = datetime.strptime(item["numberdate"], "%Y%m%d").date()
            if item_date > two_months_ago.date():
                item["start_date"] = item_date
                filtered_data.append(item)
        return filtered_data

    def gen_random_int(self):
        random_15_digit_number = random.randint(10**14, (10**15) - 1)
        return random_15_digit_number

    def _parse_detail(self, response):
        """Parse the HTML detail response for each meeting"""
        start_date = response.meta["start_date"]
        meeting_id = response.meta["meeting_id"]
        if re.search("no access", response.text, re.IGNORECASE):
            # For unknown reasons, some URLs return some HTML that includes a
            # "No access" message. This might be because the meeting is not
            # public or information is not yet available.
            self.logger.warning(
                f'"No access" found in the HTML of meeting {meeting_id} ({start_date})'
            )
            self.logger.warning("Aborting parse of this meeting.")
            return
        title = self._parse_title(response)
        meeting = Meeting(
            title=title,
            description=self._parse_description(response),
            classification=self._parse_classification(title),
            start=self._parse_start(response, start_date),
            end=None,
            all_day=False,
            time_notes="",
            location=self.location,
            links=[self.meeting_materials],
            source=response.url,
        )
        meeting["status"] = self._get_status(meeting)
        meeting["id"] = self._get_id(meeting)
        yield meeting

    def _parse_title(self, response):
        return response.css(".meeting-name::text").get().strip()

    def _parse_start(self, response, start_date):
        """
        Extracts the meeting start time from the description and combines
        it with the start_date. Assumes the time is always before the "│"
        character.
        """
        description_text = response.css(".meeting-description::text").get()
        time_match = re.search(r"(\d{1,2}:\d{2}\s*[apAP]\.?[mM]\.?)", description_text)
        if time_match:
            time_str = time_match.group(1)
            time_str_cleaned = time_str.replace(".", "")
            time_obj = datetime.strptime(time_str_cleaned, "%I:%M %p").time()
            return datetime.combine(start_date, time_obj)
        else:
            # If no time is found, return the start_date at midnight
            return datetime.combine(start_date, datetime.min.time())

    def _parse_description(self, response):
        """
        Extracts the meeting description and cleans the HTML tags, removes
        the time and pipe if present, and normalizes the whitespace.
        """
        description_html = response.css(".meeting-description").get()
        soup = BeautifulSoup(description_html, "html.parser")
        cleaned_text = soup.get_text(separator=" ", strip=True)
        # remove the time and pipe if present
        cleaned_text = re.sub(
            r"^\d{1,2}:\d{2}\s*[apAP]\.?[mM]\.?\s*│\s*", "", cleaned_text, 1
        )
        normalized_text = " ".join(cleaned_text.split())
        return normalized_text

    def _parse_classification(self, title):
        clean_title = title.lower()
        if "board" in clean_title:
            return BOARD
        return NOT_CLASSIFIED
