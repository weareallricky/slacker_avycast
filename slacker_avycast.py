#!/usr/bin/env python3
"""Posts latest avalanche forecast to Slack in a message"""
from datetime import datetime
import time
import os
import sqlite3
import traceback

import requests
from requests.exceptions import HTTPError
from dateutil import tz
from bs4 import BeautifulSoup
from dotenv import load_dotenv


class AvyForecast:
    """Model of avalanche forecast retrieved from avalanche.org API """
    danger_scale = (
            "Unknown",
            "Low",
            "Moderate",
            "Considerable",
            "High",
            "Extreme"
            )
    elevations = ("lower", "middle", "upper")

    def __init__(self, forecast_json, forecast_tz="UTC"):
        """Sets object properties from forecast JSON"""
        self.forecast_tz = forecast_tz
        self.published_time = self.get_dtobj_fromstr(
                forecast_json["published_time"]
                )
        self.expires_time = self.get_dtobj_fromstr(
                forecast_json["expires_time"]
                )
        self.author = forecast_json["author"]
        self.danger = forecast_json["danger"]
        self.bottom_line = self.strip_tags(forecast_json["bottom_line"])
        self.set_danger_max()

    def strip_tags(self, html):
        """Trims html tags from string"""
        soup = BeautifulSoup(html, features="html.parser")
        return soup.get_text()

    def get_dtobj_fromstr(self, string, strformat="%Y-%m-%dT%H:%M:%S%z"):
        """Returns timezone-ified datetime object from string"""
        return datetime.strptime(
                string,
                strformat
                ).astimezone(tz.gettz(self.forecast_tz))

    def set_danger_max(self, danger_max=False):
        """Set danger_max property"""
        if not danger_max:
            # figure out max danger rating for the day
            danger_max = 0
            for day in self.danger:
                if day["valid_day"] == "current":
                    for i in self.elevations:
                        if day[i] > danger_max:
                            danger_max = day[i]
        self.danger_max = danger_max


class AvyForecastSlackMessage:
    """Model representing an avy forecast Slack message"""
    def __init__(self,
                 avy_forecast,
                 header="Avalanche Forecast",
                 full_forecast_url="http://avalanche.org"):
        """Sets object properties from AvyForecast object"""
        self.avy_forecast = avy_forecast
        self.full_forecast_url = full_forecast_url
        self.slack_message_header = header

    def msg_format_time(self, timestamp):
        """Format timestamp in Slack-message-friendly way"""
        message_time_format = "%A, %B %d, %Y - %I:%M%p"
        return timestamp.strftime(message_time_format)

    def generate_payload(self):
        """Prepare and format Slack message JSON payload"""
        formatted_published_time = self.msg_format_time(
                self.avy_forecast.published_time
                )
        formatted_expires_time = self.msg_format_time(
                self.avy_forecast.expires_time
                )
        danger_level = forecast \
            .danger_scale[self.avy_forecast.danger_max]
        payload = {
            "text": {
                "type": "plain_text",
                "text": "New avalanche forecast"
                },
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{self.slack_message_header}"
                        }
                    },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": "*Published:*\n"
                                    f"{formatted_published_time}"
                            },
                        {
                            "type": "mrkdwn",
                            "text": "*Expires:*\n"
                                    f"{formatted_expires_time}"
                            }
                        ]
                    },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": "*Author:*\n"
                                    f"{self.avy_forecast.author}"
                                }
                        ]
                    },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Overall danger:*\n"
                                f":avy-danger-{danger_level}: "
                                f"{danger_level}"
                        }
                    },
                {
                    "type": "section",
                    "text": {
                            "type": "mrkdwn",
                            "text": "*Bottom line:*\n"
                                    f"{self.avy_forecast.bottom_line}"
                            }
                    },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"<{self.full_forecast_url}|"
                                "Read full forecast>"
                        }
                    }
                ]
            }
        return payload


def get_forecast_json(url):
    """Fetch JSON from a url eg avalanche forecast API"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        return ""


def get_avy_forecast_endpoint(forecast_center_id, forecast_zone_id):
    """Return avy forecast API endpoint URL"""
    return "https://api.avalanche.org/v2/public/product" \
        "?type=forecast" \
        f"&center_id={forecast_center_id}"\
        f"&zone_id={forecast_zone_id}"


def get_db_connection(db_location):
    """Returns SQLite db connection; prepares latest_forecast table"""
    conn = sqlite3.connect(db_location)
    conn.execute('''CREATE TABLE IF NOT EXISTS latest_forecast
            (id INTEGER PRIMARY KEY,
            published_time timestamp);''')
    return conn


if __name__ == "__main__":
    load_dotenv()
    slacker_avycast_tz = os.getenv("SLACKER_AVYCAST_TZ", "US/PACIFIC")
    webhook_url = os.getenv("SLACKER_AVYCAST_WEBHOOK_URL")
    avy_forecast_endpoint = get_avy_forecast_endpoint(
            os.getenv("SLACKER_AVYCAST_FORECAST_CENTER_ID"),
            os.getenv("SLACKER_AVYCAST_FORECAST_ZONE_ID")
            )
    forecast_check_interval = int(os.getenv(
        "SLACKER_AVYCAST_FORECAST_CHECK_INTERVAL",
        "3600"
        ))
    slack_message_header = os.getenv(
            "SLACKER_AVYCAST_SLACK_MESSAGE_HEADER",
            "Avalanche Forecast"
            )
    avy_forecast_url = os.getenv("SLACKER_AVYCAST_FULL_FORECAST_URL")
    db_file_location = os.getenv(
            "SLACKER_AVYCAST_DB_LOCATION",
            "slacker_avycast.db"
            )

    while True:
        # fetch forecast
        try:
            forecast = AvyForecast(
                    get_forecast_json(avy_forecast_endpoint),
                    slacker_avycast_tz
                    )
        except Exception as err:
            print("An exception occurred while attempting to fetch the "
                  "avalanche forecast:")
            print(traceback.format_exc())
            continue

        db = get_db_connection(db_file_location)
        cursor = db.cursor()
        record = cursor.execute(
                "SELECT published_time FROM latest_forecast WHERE id=1;"
                ).fetchone()
        cursor.close()
        if record and forecast.published_time <= datetime.strptime(
                record[0], "%Y-%m-%d %H:%M:%S%z"):
            db.close()
            time.sleep(forecast_check_interval)
            continue

        db.execute(
                "INSERT OR REPLACE INTO latest_forecast"
                "(id, published_time)"
                "VALUES (1, ?);",
                (forecast.published_time,)
                )
        db.commit()
        db.close()

        # post Slack message
        try:
            slack_message = AvyForecastSlackMessage(
                    forecast,
                    slack_message_header,
                    avy_forecast_url
                    )

            requests.post(
                    webhook_url,
                    json=slack_message.generate_payload(),
                    timeout=30
                    )
        except Exception as err:
            print("An exception occurred while attempting to post the "
                  "Slack message:")
            print(traceback.format_exc())

        del forecast
        del slack_message
