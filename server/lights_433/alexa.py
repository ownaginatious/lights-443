#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from flask_ask import Ask, statement, question
from Levenshtein import jaro


_MATCH_THRESHOLD = 0.8
_CARD_TITLE = "Home Lighting"


class ActionParseError(Exception):
    pass


class AlexaServer(object):

    def __init__(self, lights_433_server):
        self.server = lights_433_server
        self.ask = Ask(self.server.app, '/switch_alexa')
        self.ask.intent('LightSwitch')(
            lambda location, operation:
                self.perform_switch(location, operation)
        )
        self.ask.intent('AMAZON.HelpIntent')(
            lambda: self.get_welcome_response()
        )

    def match_location(self, location):
        """
        We will mutate the score a bit to add +0.1 to the jaro distance
        for starting with the same letter. Alexa's speech processing system
        really sucks at this.

        location -- the location to match against
        """
        if location:
            matches = []
            for switch_id, switch_func in self.server.switches.items():
                similarity = jaro(location, switch_id)
                if location[0].lower() == switch_id[0].lower():
                    similarity += 0.1
                matches += [(similarity, switch_id, switch_func)]
            matches.sort(key=lambda x: x[0], reverse=True)
            if matches[0][0] >= _MATCH_THRESHOLD:
                return matches[0][1:]
        raise ActionParseError("I didn't understand the location. "
                               "Could you please repeat?")

    def match_operation(self, operation):
        if operation.lower() in ('on', 'up', 'in'):
            return 'on'
        elif operation.lower() in ('off', 'down', 'out'):
            return 'off'
        raise ActionParseError("I didn't understand the operation. "
                               "Could you please repeat?")

    def perform_switch(self, location, operation):

        try:
            resolved_location = self.match_location(location or "")
            resolved_operation = self.match_operation(operation or "")
        except ActionParseError as ape:
            return question(str(ape)).simple_card(_CARD_TITLE, str(ape))

        switch_id, switch_func = resolved_location
        try:
            r = switch_func(resolved_operation)
            text = "%s %s!" % (
                switch_id.replace('_', ' ').title(), resolved_operation)
            status = int(r.status.split(' ')[0])
            if status < 200 or status > 299:
                raise Exception(status)
        except Exception:
            text = "I had problems communicating with your device!"
        return statement(text).simple_card(_CARD_TITLE, text)

    def get_welcome_response(self):
        text = "Ask me to turn your lights on and off!"
        return statement(text).simple_card(_CARD_TITLE, text)
