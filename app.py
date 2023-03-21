import logging
import sys
import time
from datetime import datetime
from typing import Iterator
import routeros_api
import json
import pymongo

from flask import Flask, Response, render_template, request, stream_with_context

logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

application = Flask(__name__)


@application.route("/")
def index() -> str:
    return render_template("index.html")

def datas() -> Iterator[str]:
    try:

        myclient = pymongo.MongoClient("mongodb://localhost:27017/")

        mydb = myclient["RealTimeTraffic"]
        collection = mydb.device.find_one({"_id": 1})
        connection = routeros_api.RouterOsApiPool(collection["address"],
                                                  port=int(collection["port"]),
                                                  username=collection["name"],
                                                  password=collection["password"],
                                                  plaintext_login=True
                                                  )
        api = connection.get_api()
        interface = api.get_resource('/interface')
        data = "0.MainLink"
        while True:
            
            stats = interface.call(
                'monitor-traffic', {'interface': data, 'once': ''})
            rx_bytes = int(stats[0]['rx-bits-per-second'])
            tx_bytes = int(stats[0]['tx-bits-per-second'])
            # rxbitToMbps = round(rx_bytes/1000)
            rxbitToMbps = rx_bytes/1000000
            txbitToMbps = tx_bytes/1000000
            # print(round(rxbitToMbps))
            # print(round(txbitToMbps))

            jso_data = json.dumps(
                {
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "rx_speed": rxbitToMbps,
                    "tx_speed": txbitToMbps
                }
            )
            # print(jso_data)
            yield f"data:{jso_data}\n\n"
            time.sleep(2)
    except GeneratorExit:
        logger.info("Client %s disconnected")


@application.route("/chart-data")
def chart_data() -> Response:
    response = Response(stream_with_context(datas()),
                        mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response


if __name__ == "__main__":
    application.run(host="0.0.0.0")
