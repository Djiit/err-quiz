# coding: utf-8
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)

import re
from time import sleep
from itertools import chain
from errbot import BotPlugin, botcmd, re_botcmd


CONFIG_TEMPLATE = {'CHATROOMS': (),
                   'QUESTION_TIMEOUT': 30,
                   'MAX_SCORE': 100}

# DEV ONLY
DEV_QUESTIONS_SET = [{
    'text': 'What is your favorite color?',
    'answer': 'blue'}]


class QuizPlugin(BotPlugin):
    """Basic Err integration with meetup.com"""

    min_err_version = '3.2.3'
    # max_err_version = '3.3.0'

    running = False
    sets = [DEV_QUESTIONS_SET]
    scores = {}
    current_question = {}

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

    def ask_question(self):
        """Ask a question on the chatroom."""
        chatrooms = (self.config['CHATROOMS']
                     if self.config['CHATROOMS']
                     else self.bot_config.CHATROOM_PRESENCE)

        for room in chatrooms:
            self.send(room,
                      self.current_question['text'],
                      message_type='groupchat')

        return

    def draw_question(self):
        """TODO"""
        self.current_question = self.sets[0][0]
        return

    def next_question(self):
        """TODO"""
        self.draw_question()
        self.ask_question()
        return

    @re_botcmd(pattern=r'', prefixed=False, flags=re.IGNORECASE)
    def quiz_answer_callback(self, mess, match):
        """Check if submitted answers are correct."""
        if not self.running or len(mess.body) == 0:
            return

        if mess.body == self.current_question['answer']:
            if str(mess.frm) in self.scores:
                self.scores[str(mess.frm)] += 1
            else:
                self.scores[str(mess.frm)] = 1
            self.next_question()
            self.start_poller(self.config['QUESTION_TIMEOUT'], self.next_question)
            return 'Well done, {0}!'.format(mess.frm)
        return

    @botcmd()
    def quiz_start(self, mess, args):
        """Start a quiz session."""
        self.scores = {}
        self.running = True
        yield '\n'.join(['New quiz session starting !',
                         'Are you ready ? First question in 5sec.'])
        #sleep(5)
        self.next_question()
        return

    @botcmd()
    def quiz_stop(self, mess, args):
        """Stop a quiz session."""
        self.running = False
        return 'Quiz Session finished.'

    @botcmd()
    def quiz_next(self, mess, args):
        """Skip the current question, if any."""
        pass

    @botcmd()
    def quiz_scores(self, mess, args):
        """Display the current scores."""
        return self.scores
