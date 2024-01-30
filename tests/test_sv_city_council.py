from datetime import datetime
from os.path import dirname, join

import pytest  # noqa
from city_scrapers_core.constants import CITY_COUNCIL, TENTATIVE
from city_scrapers_core.utils import file_response
from freezegun import freeze_time

from city_scrapers.spiders.sv_city_council import SvCityCouncilSpider

# File response setup
test_response = file_response(
    join(dirname(__file__), "files", "sv_city_council.html"),
    url="https://spokanevalley.granicus.com/ViewPublisher.php?view_id=3",
)
spider = SvCityCouncilSpider()

# Freeze time to the date of the meeting
freezer = freeze_time("2024-01-30")
freezer.start()

# Parse items
parsed_items = [item for item in spider.parse(test_response)]

# Stop time freeze
freezer.stop()


def test_count():
    assert len(parsed_items) == 10


def test_title():
    assert parsed_items[0]["title"] == "Council Meeting"


def test_description():
    assert parsed_items[0]["description"] == ""


def test_start():
    assert parsed_items[0]["start"] == datetime(2024, 1, 30, 18, 0)


def test_end():
    assert parsed_items[0]["end"] is None


def test_time_notes():
    assert parsed_items[0]["time_notes"] is None


def test_id():
    assert parsed_items[0]["id"] == "sv_city_council/202401301800/x/council_meeting"


def test_status():
    assert parsed_items[0]["status"] == TENTATIVE


def test_location():
    assert parsed_items[0]["location"] == {
        "name": "City Hall",
        "address": "10210 E Sprague Ave, Spokane Valley, WA 99206",
    }


def test_source():
    assert (
        parsed_items[0]["source"]
        == "https://spokanevalley.granicus.com/ViewPublisher.php?view_id=3"
    )


def test_links():
    assert parsed_items[0]["links"] == [
        {
            "href": "//spokanevalley.granicus.com/AgendaViewer.php?view_id=3&event_id=1314",  # noqa
            "title": "Agenda",
        }
    ]


def test_classification():
    assert parsed_items[0]["classification"] == CITY_COUNCIL


def test_all_day():
    assert parsed_items[0]["all_day"] is False
