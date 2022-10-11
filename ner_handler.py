import joblib
import calendar
import chatbot_logger


import torch
import re
from simpletransformers.ner import NERModel

model = joblib.load("ner_classifier_nmp.joblib") #Loading pickled model
      
new_labels_enum = {"PER":"PERSON","LOC":"GPE","ORG":"ORGANIZATION","MISC":"MISCELLANEOUS"}

begin_ent = re.compile("B-[A-Za-z]+")

#This groups entities that should be together. The Model for example predicts "San" as B-LOC and "Fransisco" as I-LOC. This function groups these as "San Fransisco" with a new label of GPE
def group_split_entities(predictions):
  entities = {}
  list_prediction = list(predictions[0])
  for i in range(0,len(list_prediction)):
    end_entity = ""
    list_ent = list_prediction[i]
    entity = list(list_ent.keys())[0]
    if list_ent[entity] == "O" or re.match("I-[A-Za-z]+",list_ent[entity]):
      continue
    elif begin_ent.match(list_ent[entity]):
        end_entity = list_ent[entity][2:]
        valid_ent=True
        new_entity = entity
        i=i+1
        while i< len(list_prediction) and valid_ent:
          list_ent=list_prediction[i]
          entity = list(list_ent.keys())[0]
          if re.match("I-"+end_entity,list_ent[entity]):
            new_entity = new_entity+" "+entity
            i+=1
          else:
            valid_ent = False        
        entities = {**entities, new_entity:new_labels_enum[end_entity]}
        
    else:
      entities = {**entities,entity:list_ent[entity]}
    
  return entities

#Returns a list of all entities in a users input
def predict_ner(user_input):
    prediction, _ = model.predict([user_input])
    grouped_entities = group_split_entities(prediction)
    chatbot_logger.log_prediction("Making NER Predictions",user_input,grouped_entities)
    return grouped_entities

#Returns a list of entities based on the required type
def get_entity(user_input,entity_type):
  predictions = predict_ner(user_input)
  people = [k for k in predictions.keys() if predictions[k]==entity_type]
  return people


from datetime import date, timedelta
import difflib

#This function uses a mix of heuristics and the NER Model to return a date based on the users. Specifically it handles dates that are not in a standar dd-mm-yyyy format
def search_by_weekday(predictions,input_split):
  input_split = [x.lower() for x in input_split]
  last_week = False
  error = False
  weekday = -1
  today = date.today()
  target_date = ""

  if 'today' in input_split: return str(today)
  if 'yesterday' in input_split: return str(today-timedelta(days=1))
  
  if 'week' in predictions.keys():
      pre_week_pos = input_split.index('week')-1
      if pre_week_pos>-1 and input_split[pre_week_pos].lower() == "last":
        last_week = True

  if last_week:
    del predictions['week']
    
  for key in predictions.keys():
    predictions[key]
    if predictions[key] =='DATE':
      days_of_week =[day.upper() for day in calendar.day_name]
      day = difflib.get_close_matches(key.upper(), days_of_week)[0]
      weekday = days_of_week.index(day)
      break

  
  time_delta=timedelta(days=-today.weekday()+weekday)
  start = today + time_delta
  if not last_week:
    potential_days = list(filter(lambda v: re.match('([0-9])', v), input_split))
    if len(potential_days)>0:
      target = today - timedelta(days=int(potential_days[0]))
    else:
      offset = (today.weekday() - weekday) % 7
      target = today - timedelta(days=offset)
    
  else:
    target = start - timedelta(days=7)
  target_date = str(target)

  return target_date

#This function uses the NER Model and regular expressions to look for date like entitites to return a date based on the users.
def get_date(user_input):
  predictions = predict_ner(user_input)
  input_split = user_input.split(" ")
  potential_dates = list(filter(lambda v: re.match('(^(0[1-9]|[12][0-9]|3[01])(-|\/)(0[1-9]|1[0-2])(-|\/)\d{4}$)', v), input_split))
  target_date = ""
  if len(potential_dates)>0:
    target_date=potential_dates[0]
  else:
    target_date = search_by_weekday(predictions,input_split)

  return target_date