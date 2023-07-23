"""Task Manager"""
import json
import logging
import os
import queue
import threading
import uuid

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
import requests

_LOGGER = logging.getLogger(__name__)


class TaskManager:
    """Task Manager"""

    def __init__(self):
        """Create task queue and open webdriver"""
        self.base_url = os.environ.get("BASE_URL", "")
        self.image_dir = os.environ.get("IMAGE_DIR", "images")
        os.makedirs(self.image_dir, exist_ok=True)
        self.discord_webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "")
        self.task_queue = queue.Queue()
        self.driver = self.open_webdriver()

    @staticmethod
    def open_webdriver():
        """Open webdriver and maximize window"""
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument('--headless')
        driver = webdriver.Chrome(options=options)
        driver.set_window_size(1728, 1080)

        return driver

    def start(self):
        """Create and start worker thread"""
        thread = threading.Thread(target=self.run)
        thread.start()

    def run(self):
        """Run task manager"""
        while True:
            task = self.task_queue.get()
            self.process_task(task)

    def add_task(self, task):
        """Add task to task queue"""
        self.task_queue.put(task)

    def process_task(self, payload):
        """Process task
            send message first, screenshot when ready
        """
        try:
            message = payload.get("message", "")
            self.send_message(message)
        except:
            _LOGGER.error("Error while sending message: %s", json.dumps(payload), exc_info=True)

        try:
            message = payload.get("message", "")
            chart_id = payload.get("chart_id", "")
            exchange = payload.get("exchange", "")
            symbol = payload.get("symbol", "")
            interval = payload.get("interval", "")

            image_file_name = self.maybe_save_screenshot(chart_id, exchange, symbol, interval)
            self.send_screenshot(message, image_file_name)
        except:
            _LOGGER.error("Error while processing task: %s", json.dumps(payload), exc_info=True)

    def maybe_save_screenshot(self, chart_id, exchange, symbol, interval):
        """Save screenshot"""
        if not chart_id or not self.base_url:
            return None
        url = self.gen_url(chart_id, exchange, symbol, interval)
        self.driver.get(url)

        # hide watchlist
        element = WebDriverWait(self.driver, 5).until(expected_conditions.element_to_be_clickable(
            (By.XPATH, "//button[@aria-label='Watchlist, details and news']")))
        element.click()

        image_file_name = f"{uuid.uuid4().hex}.png"
        self.driver.save_screenshot(os.path.join(self.image_dir, image_file_name))

        return image_file_name

    def gen_url(self, chart_id, exchange, symbol, interval):
        """Generate url"""
        url = f"{self.base_url}chart/{chart_id}/"
        sep = "?"
        if exchange and symbol:
            url += f"{sep}symbol={exchange}%3A{symbol}"
            sep = "&"
        elif symbol:
            url += f"{sep}symbol={symbol}"
            sep = "&"

        if interval:
            url += f"{sep}interval={interval}"

        return url

    def send_message(self, message):
        """Send message"""

        if not message or not self.discord_webhook_url:
            return

        payload = {"content": message}

        response = requests.post(self.discord_webhook_url, json=payload)
        response.raise_for_status()

    def send_screenshot(self, message, image_file_name):

        if image_file_name is None or not self.discord_webhook_url:
            return

        payload = {"content": message}
        files = {"screenshot": open(os.path.join(self.image_dir, image_file_name), "rb")}

        response = requests.post(self.discord_webhook_url, data={"payload_json": json.dumps(payload)}, files=files)
        response.raise_for_status()
