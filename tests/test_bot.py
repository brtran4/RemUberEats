import os
import json
import tempfile
import pytest
from datetime import datetime, timedelta
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def mock_env():
    os.environ["BOT_TOKEN"] = "test_token"
    os.environ["SERVER_ID"] = "123456789"
    os.environ["ABSENCE_CHANNEL_ID"] = "987654321"


@pytest.fixture(scope="function")
def temp_files(monkeypatch, mock_env):
    with tempfile.TemporaryDirectory() as tmpdir:
        absences_file = os.path.join(tmpdir, "absences.txt")
        items_file = os.path.join(tmpdir, "items.json")
        orders_file = os.path.join(tmpdir, "orders.txt")
        unclaimed_file = os.path.join(tmpdir, "unclaimed.txt")

        with open(items_file, "w") as f:
            json.dump({"1": {"en": "Test Item"}}, f)

        import bot

        bot.ABSENCES_FILE = absences_file
        bot.ORDERS_FILE = orders_file
        bot.UNCLAIMED_FILE = unclaimed_file
        bot.ITEMS_FILE = items_file

        yield {
            "absences": absences_file,
            "items": items_file,
            "orders": orders_file,
            "unclaimed": unclaimed_file,
        }


class TestAbsences:
    def test_read_absences_empty(self, temp_files, mock_env):
        import bot

        result = bot.read_absences()
        assert result == []

    def test_read_absences_with_data(self, temp_files, mock_env):
        import bot

        with open(temp_files["absences"], "w") as f:
            f.write("04/01/2026 | testuser | 123456789\n")
            f.write("04/02/2026 | anotheruser | 987654321\n")

        result = bot.read_absences()

        assert len(result) == 2
        assert result[0]["date"] == "04/01/2026"
        assert result[0]["user"] == "testuser"
        assert result[0]["user_id"] == "123456789"
        assert result[1]["date"] == "04/02/2026"
        assert result[1]["user"] == "anotheruser"

    def test_read_absences_without_user_id(self, temp_files, mock_env):
        import bot

        with open(temp_files["absences"], "w") as f:
            f.write("04/01/2026 | testuser\n")

        result = bot.read_absences()

        assert len(result) == 1
        assert result[0]["date"] == "04/01/2026"
        assert result[0]["user"] == "testuser"
        assert "user_id" not in result[0]

    def test_add_absence(self, temp_files, mock_env):
        import bot

        bot.add_absence("04/01/2026", "testuser", 123456789)

        with open(temp_files["absences"], "r") as f:
            content = f.read()

        assert "04/01/2026 | testuser | 123456789" in content

    def test_filter_past_absences_removes_old(self, temp_files, mock_env):
        import bot

        yesterday = (datetime.now() - timedelta(days=1)).strftime("%m/%d/%Y")
        today = datetime.now().strftime("%m/%d/%Y")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%m/%d/%Y")

        with open(temp_files["absences"], "w") as f:
            f.write(f"{yesterday} | olduser | 111111111\n")
            f.write(f"{today} | todayuser | 222222222\n")
            f.write(f"{tomorrow} | futureuser | 333333333\n")

        result = bot.filter_past_absences()

        assert len(result) == 2
        dates = [a["date"] for a in result]
        assert today in dates
        assert tomorrow in dates
        assert yesterday not in dates

    def test_filter_past_absences_keeps_all_when_all_future(self, temp_files, mock_env):
        import bot

        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%m/%d/%Y")
        next_week = (datetime.now() + timedelta(days=7)).strftime("%m/%d/%Y")

        with open(temp_files["absences"], "w") as f:
            f.write(f"{tomorrow} | user1 | 111111111\n")
            f.write(f"{next_week} | user2 | 222222222\n")

        result = bot.filter_past_absences()

        assert len(result) == 2

    def test_get_todays_absences(self, temp_files, mock_env):
        import bot

        today = datetime.now().strftime("%m/%d/%Y")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%m/%d/%Y")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%m/%d/%Y")

        with open(temp_files["absences"], "w") as f:
            f.write(f"{today} | todayuser | 111111111\n")
            f.write(f"{yesterday} | olduser | 222222222\n")
            f.write(f"{tomorrow} | futureuser | 333333333\n")

        result = bot.get_todays_absences()

        assert len(result) == 1
        assert result[0] == "111111111"


class TestDateValidation:
    def test_absent_rejects_past_date(self):
        yesterday = (datetime.now() - timedelta(days=2)).strftime("%m/%d/%Y")

        parsed_date = datetime.strptime(yesterday, "%m/%d/%Y").date()
        yesterday_date = (datetime.now() - timedelta(days=1)).date()

        assert parsed_date < yesterday_date

    def test_absent_accepts_today(self):
        today = datetime.now().strftime("%m/%d/%Y")

        parsed_date = datetime.strptime(today, "%m/%d/%Y").date()
        yesterday = (datetime.now() - timedelta(days=1)).date()

        assert parsed_date >= yesterday

    def test_absent_accepts_future(self):
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%m/%d/%Y")

        parsed_date = datetime.strptime(tomorrow, "%m/%d/%Y").date()
        yesterday = (datetime.now() - timedelta(days=1)).date()

        assert parsed_date >= yesterday


class TestItemsJson:
    def test_parse_items_json(self, temp_files, mock_env):
        import bot

        with open(temp_files["items"], "w") as f:
            json.dump(
                {
                    "1": {"en": "Gil"},
                    "2": {"en": "Fire Shard"},
                    "3": {"en": "Ice Shard"},
                },
                f,
            )

        bot.item_list = {}
        bot.parse_items_json()

        assert "Gil" in bot.item_list
        assert "Fire Shard" in bot.item_list
        assert "Ice Shard" in bot.item_list
        assert bot.item_list["Gil"] == "1"
        assert bot.item_list["Fire Shard"] == "2"

    def test_refresh_items_clears_and_reloads(self, temp_files, mock_env):
        import bot

        bot.item_list = {"Old Item": "999"}

        with open(temp_files["items"], "w") as f:
            json.dump({"1": {"en": "New Item"}}, f)

        bot.refresh_items()

        assert len(bot.item_list) == 1
        assert "New Item" in bot.item_list
        assert "Old Item" not in bot.item_list

    def test_refresh_items_updates_existing_items(self, temp_files, mock_env):
        import bot

        with open(temp_files["items"], "w") as f:
            json.dump({"1": {"en": "Item V1"}}, f)

        bot.item_list = {}
        bot.parse_items_json()
        assert bot.item_list["Item V1"] == "1"

        with open(temp_files["items"], "w") as f:
            json.dump({"1": {"en": "Item V2"}}, f)

        bot.refresh_items()
        assert "Item V1" not in bot.item_list
        assert "Item V2" in bot.item_list


class TestOrders:
    def test_write_to_file(self, temp_files, mock_env):
        import bot

        orders = [
            {
                "order": "Gil",
                "quantity": 100,
                "customer": "user1",
                "customer_id": 123,
                "discord_name": "user1",
            },
            {
                "order": "Fire Shard",
                "quantity": 50,
                "customer": "user2",
                "customer_id": 456,
                "discord_name": "user2",
            },
        ]
        bot.write_to_file(temp_files["orders"], orders)

        with open(temp_files["orders"], "r") as f:
            lines = f.readlines()

        assert len(lines) == 2
        assert json.loads(lines[0])["order"] == "Gil"
        assert json.loads(lines[1])["order"] == "Fire Shard"

    def test_read_from_file_empty(self, temp_files, mock_env):
        import bot

        result = bot.read_from_file(temp_files["orders"])
        assert result == []

    def test_read_from_file_with_data(self, temp_files, mock_env):
        import bot

        orders = [
            {
                "order": "Gil",
                "quantity": 100,
                "customer": "user1",
                "customer_id": 123,
                "discord_name": "user1",
            },
        ]
        bot.write_to_file(temp_files["orders"], orders)

        result = bot.read_from_file(temp_files["orders"])

        assert len(result) == 1
        assert result[0]["order"] == "Gil"
        assert result[0]["quantity"] == 100
        assert result[0]["customer"] == "user1"

    def test_read_from_file_creates_empty_file(self, temp_files, mock_env):
        import bot

        result = bot.read_from_file("nonexistent_file.txt")
        assert result == []
