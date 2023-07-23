from flask import Flask
from flask import request

from task_manager import TaskManager

app = Flask(__name__)


@app.route('/alert', methods=['POST'])
def tradingview():
    payload = request.json or {}
    task_manager.add_task(payload)
    return "OK"


if __name__ == '__main__':
    task_manager = TaskManager()
    task_manager.start()
    app.run(host="0.0.0.0", port=80)
