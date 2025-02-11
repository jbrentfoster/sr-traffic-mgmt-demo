"""

Copyright (c) 2025 Cisco and/or its affiliates.

This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at

               https://developer.cisco.com/docs/licenses

All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.

"""

import json
import logging
import python.utils


async def send_async_request(url, user, password):
    response_json_list = []
    try:
        response = await utils.rest_get_tornado_httpclient(url, user, password)
        response_json = json.loads(response)
        if type(response_json) is dict:
            response_json_list.append(response_json)
            response = json.dumps(response_json_list, indent=2, sort_keys=True)
        # with open("../jsongets/response.json", 'w', encoding="utf8") as f:
        #     # json.dump(response, f, sort_keys=True, indent=4, separators=(',', ': '))
        #     f.write(response)
        #     f.close()
        result = {'action': 'collect', 'status': 'completed', 'body': response}
        return result
    except Exception as err:
        result = {'action': 'collect', 'status': 'failed', 'body': response}
        logging.info(response)
        return result


def get_response():
    with open("../jsongets/traffic_matrix.json", 'r', ) as f:
        response = json.load(f)
        f.close()
    return json.dumps(response)


def process_ws_message(message):
    response = "Got the message from websocket, here's my reply"
    return response
