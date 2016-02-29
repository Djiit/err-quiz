# coding: utf-8
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)

import re
import random
from threading import Timer
from time import sleep
from itertools import chain
from collections import defaultdict

from errbot import BotPlugin, botcmd, re_botcmd


CONFIG_TEMPLATE = {'CHATROOMS': (),
                   'QUESTION_TIMEOUT': 30,
                   'QUESTION_INTERVAL': 5,
                   'MAX_SCORE': 100}

# DEV ONLY
DEV_QUESTIONS_SET = [{
    'text': 'What is your favorite color?',
    'answer': 'blue'}, {
    'text': 'What does the fox says?',
    'answer': 'roar'}]


class QuizPlugin(BotPlugin):
    """Basic Err integration with meetup.com"""

    min_err_version = '3.2.3'
    # max_err_version = '3.3.0'

    def get_configuration_template(self):
        return CONFIG_TEMPLATE

    def configure(self, configuration):
        if configuration is not None and configuration != {}:
            config = dict(chain(CONFIG_TEMPLATE.items(),
                                configuration.items()))
        else:
            config = CONFIG_TEMPLATE
        super().configure(config)
        return

    def activate(self):
        super().activate()
        self.init_store('watchlist', [])
        self.init_store('playing', False)
        self.init_store('sets', [DEV_QUESTIONS_SET], True)
        self.init_store('scores', defaultdict(int))
        self.init_store('current_question', {})
        self.init_store('skip_counter', set())
        self.init_store('skipped', False)
        self.init_store('answered', False)
        self.timer = Timer(self.config['QUESTION_TIMEOUT'], self.next_question)
        return

    def init_store(self, key, default_value, force=False):
        """Boostrap the internal storage with default values"""
        if force or (key not in self):
            self[key] = default_value
        return

    def restart_timer(self):
        """Cancel old timer, create a new thread, start the new Timer."""
        if not self['playing']:
            return

        self.log.debug('Restarting timer for question')
        self.timer.cancel()
        self.timer = Timer(self.config['QUESTION_TIMEOUT'], self.next_question)
        self.timer.start()
        return

    def broadcast(self, mess):
        """Shortcut to broadcast a message to all elligible chatrooms."""
        chatrooms = (self.config['CHATROOMS']
                     if self.config['CHATROOMS']
                     else self.bot_config.CHATROOM_PRESENCE)

        for room in chatrooms:
            self.send(room, mess, message_type='groupchat')
        return

    def ask_question(self):
        """Ask a question on the chatroom(s)."""
        self.broadcast(self['current_question']['text'])
        return

    def draw_question(self):
        """Randomly choose a new question from the alvailable sets."""
        a = random.choice(self['sets'][0])
        print(a)
        self['current_question'] = a
        return

    def next_question(self):
        """Go to the next question"""
        # Did we skip the current question ?
        if self['skipped']:
            self['skip_counter'] = set()
            self.broadcast('Question skipped. The answer was "{0}".'.format(
                self['current_question']['answer']))

        # Was the question answered ?
        if not self['answered']:
            self.broadcast('Time is out! The answer was "{0}".'.format(
                self['current_question']['answer']))

        # Let's wait a little bit
        self.broadcast('Next question in {}sec.'.format(
            self.config['QUESTION_INTERVAL']))

        sleep(self.config['QUESTION_INTERVAL'])

        # set default values for next question
        self['skipped'] = False
        self['answered'] = False
        self.draw_question()
        self.ask_question()
        self.restart_timer()
        return

    @re_botcmd(pattern=r'', prefixed=False, flags=re.IGNORECASE)
    def quiz_answer_callback(self, mess, match):
        """Check if submitted answers are correct."""
        self.log.debug('Quiz answer callback called!')
        # Are we playing ? Is the message empty ?
        if not self['playing'] or len(mess.body) == 0:
            return

        if mess.body == self['current_question']['answer']:
            # well done, let's increment your score
            self['scores'][str(mess.frm)] += 1

            # tell the bot this question was answered
            self['answered'] = True

            # now to the next question
            yield 'Well done, {0}!'.format(mess.frm)
            self.next_question()
        return

    @botcmd()
    def quiz_start(self, mess, args):
        """Start a quiz session."""
        self['playing'] = True

        # Reset scores
        self['scores'] = defaultdict(int)

        # Setup default values for questions
        self['skipped'] = False
        self['answered'] = False

        yield 'New quiz session starting !'
        yield 'Are you ready ? First question in {}sec.'.format(
            self.config['QUESTION_INTERVAL'])

        sleep(self.config['QUESTION_INTERVAL'])

        # ask first question
        self.draw_question()
        self.ask_question()

        # start the timer
        self.restart_timer()
        return

    @botcmd()
    def quiz_stop(self, mess, args):
        """Stop a quiz session."""
        if not self['playing']:
            return

        self['playing'] = False

        # Stop the question poller
        self.timer.cancel()
        return 'Quiz Session finished.'

    @botcmd()
    def quiz_next(self, mess, args):
        """Skip the current question, if any."""
        # Add the user to the skip_count set.
        self['skip_counter'].add(str(mess.frm))

        # have we 3 skippers yet ?
        if len(self['skip_counter']) > 2:
            self['skipped'] = True
            self.next_question()
        return '{0} wants to skip the question ({1}/3)'.format(
            str(mess.frm), len(self['skip_counter']))

    @botcmd()
    def quiz_scores(self, mess, args):
        """Display the current scores."""
        if len(self['scores']) < 1:
            return 'No scores yet. Why not start a new game ?'
        yield 'Current scores :'
        for e in self['scores']:
            yield '{0}: {1}. '.format(e, self['scores'][e])
        return
