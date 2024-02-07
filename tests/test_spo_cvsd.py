from datetime import datetime
from os.path import dirname, join

import pytest
from city_scrapers_core.constants import BOARD, PASSED
from city_scrapers_core.utils import file_response
from freezegun import freeze_time
from scrapy.http import HtmlResponse, Request

from city_scrapers.spiders.spo_cvsd import SpokSvsdSpider

freezer = freeze_time("2024-02-07")
freezer.start()
freezer.stop()

# set up response fixtures
# Because _parse_detail expects meta data, we can't rely on the
# the file_response helper in this case. We create a response
# object from scratch.
test_response = file_response(
    join(dirname(__file__), "files", "spo_cvsd.json"),
    url="https://go.boarddocs.com/wa/cvsd/Board.nsf/BD-GetMeetingsList?open&0.320616755508751",  # noqa: E501
)
start_date = datetime(2024, 1, 22)
request_with_meta = Request(
    url="https://go.boarddocs.com/wa/cvsd/Board.nsf/BD-GetMeeting?open&0.934001628042688",  # noqa: E501
    meta={"start_date": start_date, "meeting_id": "CYXL4V54CB3F"},
)
response_body = open(
    join(dirname(__file__), "files", "spo_cvsd_detail.json"), "rb"
).read()
test_response_detail = HtmlResponse(
    url=request_with_meta.url,
    request=request_with_meta,
    body=response_body,
    encoding="utf-8",
)

# parse responses
spider = SpokSvsdSpider()
parsed_items = [item for item in spider.parse(test_response)]
parsed_item = next(spider._parse_detail(test_response_detail))


def test_count():
    assert len(parsed_items) == 6


def test_title():
    assert parsed_item["title"] == "Regular Board Meeting"


def test_description():
    expected_description = (
        "Learning and Teaching Center │ 2218 N Molter Rd Liberty Lake WA "
        'To attend the School Board Meeting virtually, copy & paste this link or click on the "Video" button: '  # noqa: E501
        "https://cvsd-org.zoom.us/j/89079384973?pwd=ue1kMxR2B7_XPZQqL56fc7rbeeYnsf.1#success"  # noqa: E501
    )
    assert parsed_item["description"] == expected_description


def test_start():
    assert parsed_item["start"] == datetime(2024, 1, 22, 18, 30)


def test_end():
    assert parsed_item["end"] is None


def test_id():
    expected_id = "spo_cvsd/202401221830/x/regular_board_meeting"
    assert parsed_item["id"] == expected_id


def test_status():
    assert parsed_item["status"] == PASSED


def test_location():
    expected_location = {
        "name": "Learning and Teaching Center",
        "address": "2218 N Molter Rd Liberty Lake WA",
    }
    assert parsed_item["location"] == expected_location


def test_source():
    expected_url = "https://go.boarddocs.com/wa/cvsd/Board.nsf/BD-GetMeeting?open&0.934001628042688"  # noqa: E501
    assert parsed_item["source"] == expected_url


def test_links():
    expected_links = [
        {
            "href": "https://www.cvsd.org/apps/pages/BoardBulletin",
            "title": "Meeting materials",
        }
    ]
    assert parsed_item["links"] == expected_links


def test_classification():
    assert parsed_item["classification"] == BOARD


@pytest.mark.parametrize("item", [parsed_item])
def test_all_day(item):
    assert item["all_day"] is False
