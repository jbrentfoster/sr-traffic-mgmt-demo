/**
 * @license
 * Copyright (c) 2025 Cisco and/or its affiliates.
 *
 * This software is licensed to you under the terms of the Cisco Sample
 * Code License, Version 1.1 (the "License"). You may obtain a copy of the
 * License at
 *
 *                https://developer.cisco.com/docs/licenses
 *
 * All use of the material herein must be in accordance with the terms of
 * the License. All rights not expressly granted by the License are
 * reserved. Unless required by applicable law or agreed to separately in
 * writing, software distributed under the License is distributed on an "AS
 * IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied.
 */

 /*
 * Contains all custom javascript code to run the web client.
 * Incorporates websockets and AJAX
 */

 $(document).ready(function() {
    console.log("Document ready!");
 });


//jQuery extended (custom) functions defined...
jQuery.fn.extend({
    cleanJSON: function(the_json) {
        // preserve newlines, etc - use valid JSON
        var s = the_json.replace(/\\n/g, "\\n")
               .replace(/\\'/g, "\\'")
               .replace(/\\"/g, '\\"')
               .replace(/\\&/g, "\\&")
               .replace(/\\r/g, "\\r")
               .replace(/\\t/g, "\\t")
               .replace(/\\b/g, "\\b")
               .replace(/\\f/g, "\\f");
        // remove non-printable and other non-valid JSON chars
        s = s.replace(/[\u0000-\u0019]+/g,"");
        return s;
    },
});

// Web client javascript functions (including websocket client code)...
var client = {
    queue: {},

    // Connects to Python through the websocket
    connect: function (port) {
        var self = this;
        console.log("Opening websocket to ws://" + window.location.hostname + ":" + port + "/websocket");
        this.socket = new WebSocket("ws://" + window.location.hostname + ":" + port + "/websocket");

        this.socket.onopen = function () {
            console.log("Connected!");
        };

        this.socket.onmessage = function (messageEvent) {
            console.log("Got a message...");
            client.buildTrafficMatrixTable(messageEvent.data)
            console.log(messageEvent.data);
        };
        return this.socket;
    },

    waitForSocketConnection: function(socket, callback) {
        setTimeout(function () {
            if (socket.readyState === 1) {
                console.log("Connection is made");
                if(callback != null){
                    callback();
                }
                return;

            } else {
                console.log("wait for connection...");
                waitForSocketConnection(callback);
            }
        }, 5); // wait 5 milisecond for the connection...
    },

    sendSocketMessage: function(message) {
         this.socket.send(JSON.stringify({method: "process_ws_message", params: {message: message}}));
    },

    buildTrafficMatrixTable: function (traffic_data) {
        var traffic_data_json = JSON.parse($().cleanJSON(traffic_data));
        const tbody = document.querySelector("#traffic-table tbody");
        tbody.innerHTML = ""; // Clear existing rows

        // Sort the data by the first column (source_router)
        traffic_data_json.sort((a, b) => {
            if (a.source_router < b.source_router) return -1;
            if (a.source_router > b.source_router) return 1;
            return 0;
        });

        traffic_data_json.forEach(row => {
            const tr = document.createElement("tr");
            tr.innerHTML = `<td>${row.source_router}</td><td>${row.dest_router}</td><td>${row.locator_addr}</td><td>${row.traffic_rate}</td>`;
            tbody.appendChild(tr);
        });

        // Update the timestamp
        const updateTimeElement = document.getElementById("update-time");
        const now = new Date();
        updateTimeElement.textContent = `Last updated: ${now.toLocaleString()}`;
    },
};

