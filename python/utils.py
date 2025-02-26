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

import requests
import json
import python.errors
import logging
from tornado import httpclient
from tornado import httputil
from urllib.parse import urlencode

# Reuse a single HTTP client instance
http_client = httpclient.AsyncHTTPClient()


async def rest_get_tornado_httpclient(url, user=None, password=None, data=None):
    """ Perform an async GET request with Tornado's HTTPClient. """

    # Encode params if provided
    if data:
        query_string = urlencode(data)
        url = f"{url}?{query_string}"

    http_request = httpclient.HTTPRequest(
        url=url,
        auth_username=user,
        auth_password=password,
        headers=httputil.HTTPHeaders({
            "content-type": "application/json",
            "accept": "application/json"
        })
    )

    try:
        response = await http_client.fetch(http_request)
        return response.body.decode(
            'utf-8') if response.code == 200 else f"Failed HTTP response...code: {response.code}"
    except Exception as err:
        logging.error(f"Error: {err}")
        return f"Error: {err}"


async def rest_post_tornado_httpclient(url, user=None, password=None, data=None):
    """ Perform an async POST request with Tornado's HTTPClient. """

    http_request = httpclient.HTTPRequest(
        url=url,
        method="POST",
        body=data,
        auth_username=user,
        auth_password=password,
        headers=httputil.HTTPHeaders({
            "content-type": "application/json",
            "accept": "application/json"
        })
    )

    try:
        response = await http_client.fetch(http_request)
        return response.body.decode('utf-8') if response.code in [200, 201,
                                                                  204] else f"Failed HTTP response...code: {response.code}"
    except Exception as err:
        logging.error(f"Error: {err}")
        return f"Error: {err}"


def rest_post_json(baseURL, uri, thejson, user, password):
    proxies = {
        "http": None,
        "https": None,
    }
    appformat = 'application/json'
    headers = {'content-type': appformat, 'accept': appformat}
    restURI = baseURL + uri
    logging.info(restURI)
    try:
        r = requests.post(restURI, data=thejson, headers=headers, proxies=proxies, auth=(user, password),
                          verify=False)
        # print "HTTP response code is: " + str(r.status_code)
        if r.status_code == 200:
            return json.dumps(r.json(), indent=2)
        else:
            raise errors.InputError(restURI, "HTTP status code: " + str(r.status_code))
    except errors.InputError as err:
        logging.error("Exception raised: " + str(type(err)))
        logging.error(err.expression)
        logging.error(err.message)
        return