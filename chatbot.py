from state_enum import STATE
import chatbot_logger
import ner_handler
import intent_handler
import sentiment_handler
import pandas as pd
from os.path import exists
import os
import csv
from datetime import date


class Chatbot:
    def __init__(self, name):
        self.name = name
        self.__change_state(STATE.GREETING)
        self.user_id = None
        self.users_name = None
        self.users_phrase = None
        self.new_entry = []

    def get_response(self, user_input):
        print(self.state)
        response = ""
        if self.state == STATE.CHECK_IF_NEW:
            response = self.confirm_profile(user_input)

        # PROFILE LOGIN
        elif self.state == STATE.LOGIN_NAME_ENTRY:
            response = self.ask_login_name(user_input)

        elif self.state == STATE.CONFIRM_LOGIN_NAME:
            response = self.confirm_login_name(user_input)

        elif self.state == STATE.LOGIN_PHRASE_ENTRY:
            response = self.ask_login_phrase(user_input)


        # PROFILE CREATION
        elif self.state == STATE.CREATE_PROFILE_NAME:
            response = self.ask_name(user_input)

        elif self.state == STATE.CONFIRM_NAME:
            response = self.confirm_name(user_input)

        elif self.state == STATE.CREATE_PROFILE_PHRASE:
            response = self.ask_phrase(user_input)

        elif self.state == STATE.CONFIRM_PHRASE:
            response = self.confirm_phrase(user_input)

        elif self.state == STATE.CONFIRM_OVERWRITE:
            response = self.confirm_overwrite(user_input)

        elif self.state == STATE.CONFIRM_VIEW_ENTRY:
            response = self.confirm_view_entry(user_input)

        elif self.state == STATE.ADD_ENTRY:
            response = self.add_entry(user_input, False)

        elif self.state == STATE.ADD_OVERWRITE:
            response = self.add_entry(user_input, True)

        elif self.state == STATE.VIEW_ENTRY:
            response = self.view_entry(user_input)

        elif self.state == STATE.CONFIRM_EXIT:
            response = self.confirm_exit(user_input)

        elif self.state == STATE.RUNNING:
            intent = intent_handler.predict_intent(user_input)

            print(intent)
            if intent == "add_entry":
                self.__change_state(STATE.CONFIRM_OVERWRITE)
                response = self.check_if_exists(user_input)

            elif intent == "entry_query":
                response = self.view_entry(user_input)

            elif intent in ["goodbye", "cancel"]:
                response = self.goodbye()
            else:
                response = "Sorry I don't understand what you're trying to do."

        chatbot_logger.log_converstion(user_input, response)
        return self.__format_response(response)

    def confirm_profile(self, user_input):
        response = ""
        intent = intent_handler.predict_intent(user_input)
        print(intent)

        if intent == "yes":
            self.__change_state(STATE.LOGIN_NAME_ENTRY)
            response = "Great! Please could you tell me your name?"

        elif intent == "no":
            self.__change_state(STATE.CREATE_PROFILE_NAME)
            response = "No worries, let's create a profile for you. What's your name?"

        elif intent in ["cancel", "goodbye"]:
            response = "Okay, have a nice day. Goodbye!"
            self.__change_state(STATE.GREETING)
        else:
            response = "Sorry, I didn't quite catch that, please could you confirm whether you've used DearBot before?"
        return response

    def __get_names(self, user_input):
        names = ner_handler.get_entity(user_input, "PERSON")
        return names if len(names) > 0 else None

    def view_entry(self, user_input):
        date = ner_handler.get_date(user_input)
        user_data = pd.read_csv('csvs/user_csvs/{}.csv'.format(self.user_id))
        user_data = user_data.to_numpy()

        entry = ""
        location = ""
        people = ""
        emotion = ""
        emoticon = ""
        for row in user_data:
            if row[0] == date:
                print(row, "exists")
                entry = row[1]
                location = self.__lst_to_list(row[2])
                people = self.__lst_to_list(row[3])
                emotion = row[4]
                emoticon = row[5]

                summary = "Here's your summary for {}\n\n".format(date) +\
                "You went to: {}\n".format(location) +\
                "You were with: {}\n".format(people) +\
                "Overall on this day you felt {} {}\n\n".format(emotion, emoticon) +\
                "This was your full entry for the day: {}\n\n".format(entry) +\
                "What else would you like to do today?"

                return summary

        return "It seems like you don't have an entry for that day. What else would you like to do?"


    def confirm_overwrite(self, user_input):
        response = ""
        intent = intent_handler.predict_intent(user_input)
        print(intent)
        if intent == "yes":
            self.__change_state(STATE.ADD_OVERWRITE)
            response = "Sure, tell me about your day!"
            print("RESPONSE ASSIGNED")
        elif intent in ["no", "cancel"]:
            self.__change_state(STATE.RUNNING)
            response = "No problem, let's leave your diary as it is. What would you like to do now?"
        elif intent == "goodbye":
            response = self.goodbye()
        else:
            response = "Sorry, please could you confirm if you would like to overwrite today's entry?"

        return response

    def check_if_exists(self, user_input):
        response = "Tell me about your day"

        intent = intent_handler.predict_intent(user_input)

        if intent in ["cancel", "no"]:
            self.__change_state(STATE.RUNNING)
            response = "No problem, you can always add to your diary later. What would you like to do now?"
        elif intent == "goodbye":
            response = self.goodbye()
        else:
            user_data = pd.read_csv('csvs/user_csvs/{}.csv'.format(self.user_id))
            user_data = user_data.to_numpy()
            for row in user_data:
                if str(row[0]) == str(date.today()):
                    self.__change_state(STATE.CONFIRM_OVERWRITE)
                    return "It seems that you've already got an entry in your diary for today. Would you like to overwrite it?"

            self.__change_state(STATE.ADD_ENTRY)

        return response

    def add_entry(self, user_input, overwrite):
        intent = intent_handler.predict_intent(user_input)

        if intent == "cancel":
            self.__change_state(STATE.RUNNING)
            response = "No worries, you can always tell me about your day some other time. What would you like to do now?"
        else:
            entry_ner = ner_handler.predict_ner(user_input)

            for item in entry_ner:
                print(item)

            locations = []
            people = []

            for key in entry_ner:
                if entry_ner[key] == 'GPE':
                    locations.append(key)
                if entry_ner[key] == 'PERSON':
                    people.append(key)

            emotion, emoticon = sentiment_handler.get_emoticon(user_input)

            if overwrite:
                f = "csvs/user_csvs/{}.csv".format(self.user_id)
                user_df = pd.read_csv(f)
                user_df = user_df.iloc[:-1, :]
                user_df.to_csv(f)

            with open('csvs/user_csvs/{}.csv'.format(self.user_id), 'a') as fd:
                writer = csv.writer(fd)
                writer.writerow([str(date.today()), str(user_input), locations, people, emotion, emoticon])
                fd.close()

            response = "Thanks for telling me about your day. This was your entry:\n{}\n" \
                       "Would you like to see today's summary?".format(user_input)
            self.__change_state(STATE.CONFIRM_VIEW_ENTRY)
        return response

    def confirm_view_entry(self, user_input):
        intent = intent_handler.predict_intent(user_input)

        if intent in ["cancel", "no"]:
            self.__change_state(STATE.RUNNING)
            response = "Okay, what else would you like to do?"
        elif intent == "yes":
            self.__change_state(STATE.RUNNING)
            today = str(date.today())
            user_data = pd.read_csv('csvs/user_csvs/{}.csv'.format(self.user_id))
            user_data = user_data.to_numpy()

            entry = ""
            location = ""
            people = ""
            emotion = ""
            emoticon = ""

            for row in user_data:
                if row[0] == today:
                    print(row, "exists")
                    location = self.__lst_to_list(row[2])
                    people = self.__lst_to_list(row[3])
                    emotion = row[4]
                    emoticon = row[5]

                    response = "Here's your summary for {}\n\n".format(today) + \
                              "You went to: {}\n".format(location) + \
                              "You were with: {}\n".format(people) + \
                              "Overall on this day you felt {} {}\n\n".format(emotion, emoticon) + \
                              "What else would you like to do today?"

        else:
            response = "Sorry I didn't catch that. Did you want to see a summary of your day today?"

        return response

    def goodbye(self):
        self.__change_state(STATE.GREETING)
        return "Thanks for using {}! Goodbye!".format(self.name)

    def ask_login_name(self, user_input):
        intent = intent_handler.predict_intent(user_input)

        if intent in ["cancel", "goodbye", "no"]:
            self.__change_state(STATE.GREETING)
            response = "Sorry, I can't help you without your name! Goodbye!"
        else:
            names = self.__get_names(user_input)

            if names is None:
                return "Sorry I didn't recognise a name? What is your name?"

            if names != None:
                self.users_name = names[0]
            self.__change_state(STATE.CONFIRM_LOGIN_NAME)
            response = "Just checking if I got that right, is your name {}?".format(self.users_name)

        return response

    def confirm_login_name(self, user_input):
        response = ""
        intent = intent_handler.predict_intent(user_input)
        if intent == "yes":
            self.__change_state(STATE.LOGIN_PHRASE_ENTRY)
            response = "Hi {}! Can you please enter your special phrase?".format(
                self.users_name)
        elif intent == "no":
            self.__change_state(STATE.LOGIN_NAME_ENTRY)
            response = "No problem, what should I call you?"
        elif intent in ["cancel", "goodbye"]:
            self.__change_state(STATE.GREETING)
            response = "Okay, no worries, see you soon! Goodbye!"
        else:
            response = "Sorry, please could you confirm if {} is your name?".format(self.users_name)

        return response

    def ask_login_phrase(self, user_input):
        self.users_phrase = user_input

        if self.users_phrase is None:
            return "Sorry I didn't recognise a phrase? Can you give me a special phrase?"

        users = pd.read_csv('csvs/users.csv')
        users = users.to_numpy()
        for user in users:
            if self.users_name == user[1] and self.users_phrase == user[2]:
                self.user_id = user[0]
                self.__change_state(STATE.RUNNING)
                return "Hi {}! Nice to see you again! What would you like to do?".format(self.users_name)

        self.__change_state(STATE.CHECK_IF_NEW)
        return "Sorry {}, but I don't think we've met before, or you may have given me the wrong details. Are you sure we've met before?".format(self.users_name)


    def ask_phrase(self, user_input):
        response = ""
        self.users_phrase = user_input
        if self.users_phrase is None:
            return "Sorry, I didn't get a phrase. Can you give me a special phrase?"

        self.state = STATE.CONFIRM_PHRASE
        response = "Is {} the phrase you'd like to use?".format(self.users_phrase)
        return response

    def confirm_phrase(self, user_input):
        response = ""
        intent = intent_handler.predict_intent(user_input)

        if intent == "yes":
            if exists('csvs/users.csv'):
                users = pd.read_csv('csvs/users.csv')
                users = users.to_numpy()

                for user in users:
                    if self.users_name == user[1] and self.users_phrase == user[2]:
                        self.__change_state(STATE.CREATE_PROFILE_PHRASE)
                        return "Sorry {}, please could you use a different phrase?".format(self.users_name)
            else:
                users = []
                os.mkdir("csvs")
                os.mkdir("csvs/user_csvs")

            self.user_id = len(users)

            with open('csvs/users.csv', 'a') as fd:
                writer = csv.writer(fd)
                writer.writerow(["user_id", "user_name", "user_phrase"])
                writer.writerow([str(self.user_id), self.users_name, self.users_phrase])
                fd.close()

            with open('csvs/user_csvs/{}.csv'.format(self.user_id), 'a') as fd:
                writer = csv.writer(fd)
                writer.writerow(['date', 'entry', 'location', 'people', 'emotion', 'emoticon'])
                fd.close()

            self.__change_state(STATE.RUNNING)
            response = "Thanks {}! Now that we've met, what would you like to do?".format(
                self.users_name)

        elif intent == "no":
            self.__change_state(STATE.CREATE_PROFILE_PHRASE)
            response = "What would you like your phrase to be instead?"

        elif intent == "cancel":
            self.__change_state(STATE.CONFIRM_EXIT)
            response = "Sorry, I can't help unless you set a phrase! Would you like to leave?"
        else:
            return "Sorry, please could you confirm if you want to use the phrase {}?".format(self.users_phrase)

        return response

    def confirm_exit(self, user_input):
        response = ""
        intent = intent_handler.predict_intent(user_input)

        if intent in ["yes", "goodbye"]:
            self.__change_state(STATE.GREETING)
            response = "Okay :( See you soon. Goodbye!"
        else:
            self.__change_state(STATE.CREATE_PROFILE_PHRASE)
            response = "Okay, please enter a special phrase.".format(self.users_name)

        return response

    def ask_name(self, user_input):
        names = self.__get_names(user_input)

        intent = intent_handler.predict_intent(user_input)

        if intent in ["cancel", "no", "goodbye"]:
            self.__change_state(STATE.GREETING)
            return "Okay. See you next time. Goodbye!"
        else:
            if names is None:
                return "Sorry I didn't recognise a name? What is your name?"

            if names != None:
                self.users_name = names[0]
            self.__change_state(STATE.CONFIRM_NAME)
            response = "Just checking if I got that right, is your name {}?".format(self.users_name)

        return response

    def confirm_name(self, user_input):
        response = ""
        intent = intent_handler.predict_intent(user_input)

        if intent == "yes":
            self.__change_state(STATE.CREATE_PROFILE_PHRASE)
            response = "Hi {}! Can you please give me a special phrase that you'll use to access your diary?".format(
                self.users_name)

        elif intent == "no":
            self.__change_state(STATE.CREATE_PROFILE_NAME)
            response = "What is your name then?"

        elif intent in ["cancel", "goodbye"]:
            self.__change_state(STATE.GREETING)
            response = "Sorry, I can't recognise you without your name.. Goodbye!"

        else:
            return "Sorry, please could you confirm if {} is your name?".format(self.users_name)

        return response

    def choose_what_to_do(self, user_input):
        pass

    def say_greeting(self):
        response = ""
        if self.state == STATE.GREETING:
            self.__change_state(STATE.CHECK_IF_NEW)
            response = "Hey there! Have you used {} before?".format(self.name)
        return self.__format_response(response)

    def __format_response(self, response):
        return {"response": response, "state": self.state.value}

    def __change_state(self, state: STATE):
        self.state = state
        chatbot_logger.log_bot_state(self.state.name)

    def __lst_to_list(self,str_list):
        new_val = str_list.replace('\'', '')
        return new_val.strip('][')

