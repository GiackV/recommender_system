# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


# This is a simple example for a custom action which utters "Hello World!"

from typing import Any, Text, Dict, List
import datetime as dt
import requests
from geopy.geocoders import Nominatim

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, Restarted
import json
import math 


class RestaurantAPI:
    def __init__(self):
        # initialize Nominatim API
        self.geolocator = Nominatim(user_agent="geoapi_test")

    def search(self, tracker):
        # get slot informations
        food = tracker.get_slot("food")
        pricerange = tracker.get_slot("price")
        people = tracker.get_slot("people")
        location = tracker.get_slot("place")
        lat, lng = self._loc2coord(location)
        
        # API CALL
        url = "https://travel-advisor.p.rapidapi.com/restaurants/v2/list"
        querystring = {"currency":"EUR","units":"km","lang":"en_US"}

        sort            = "POPULARITY"
        partySize       = self._convertWord2Num(people)
        meal_type       = 10599
        price           = "10953, 10954, 1955" if pricerange is None else "10953" if pricerange == "cheap" else "10955" if pricerange == "moderate" else 10954 # if "expensive"
        cuisine         = self._find_cuisine(food) # assumed the user specifies only one cuisine
        #diet            = 
        min_rating      = 30
        distance        = 2 # Km
        bbox = self._getBoundsFromLatLng(lat, lng, distance)

        payload = """{\r
            \"geoId\": 1,\r
            \"partySize\": """+ str(partySize) +""",\r
            \"reservationTime\": \"2021-07-07T20:00\",\r
            \"sort\": \""""+ str(sort) +"""\",\r
            \"sortOrder\": \"desc\",\r
            \"filters\": [\r
                {\r
                    \"id\": \"establishment\",\r
                    \"value\": [\r
                        \"10591\"\r
                    ]\r
                },\r
                {\r
                    \"id\": \"meal\",\r
                    \"value\": [\r
                        \""""+ str(meal_type) +"""\"\r
                    ]\r
                },\r
                {\r
                    \"id\": \"price\",\r
                    \"value\": [\r
                        \""""+ str(price) +"""\"\r
                    ]\r
                },\r
                {\r
                    \"id\": \"minRating\",\r
                    \"value\": [\r
                        \""""+ str(min_rating) +"""\"\r
                    ]\r
                },\r
                {\r
                    \"id\": \"cuisine\",\r
                    \"value\": [\r
                        \""""+ str(cuisine) +"""\"\r
                    ]\r
                }\r
            ],\r
            \"boundingBox\": {\r
                \"northEastCorner\": {\r
                    \"latitude\": """+ str(bbox["lat_max"]) +""",\r
                    \"longitude\": """+ str(bbox["lon_max"]) +"""\r
                },\r
                \"southWestCorner\": {\r
                    \"latitude\": """+ str(bbox["lat_min"]) +""",\r
                    \"longitude\": """+ str(bbox["lon_min"]) +"""\r
                }\r
            },\r
            \"updateToken\": \"\"\r
        }"""

        headers = {
            'content-type': "application/json",
            'x-rapidapi-host': "travel-advisor.p.rapidapi.com",
            'x-rapidapi-key': "ce62ea5053msh91c49554fdff0dap14f015jsn57264a71a9c7"
        }

        try:
            response = requests.request("POST", url, data=payload, headers=headers, params=querystring)
            data = json.loads(response.text)["data"]
            data = data["AppPresentation_queryAppListV2"][0]

            data = data["sections"]
            options = []
            for i in range(len(data)):
                if "singleCardContent" in data[i]:
                    options.append(data[i])
            return options
        except:
            return None

    def _loc2coord(self, location):
        area = self.geolocator.geocode(location).raw

        # Get latitude and longitude
        return area['lat'], area['lon']
    
    def _getBoundsFromLatLng(self, lat, lng, radiusInKm):
        lat = float(lat)
        lng = float(lng)
        lat_change = radiusInKm/111.2
        lon_change = abs(math.cos(lat*(math.pi/180)))
        bounds = { 
            "lat_min": lat - lat_change,
            "lon_min": lng - lon_change,
            "lat_max": lat + lat_change,
            "lon_max": lng + lon_change
        }
        return bounds
    
    def _convertWord2Num(self, number): 
        units = [
            "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
            "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
            "sixteen", "seventeen", "eighteen", "nineteen", "twenty"
        ]
        for i, unit in enumerate(units):
            if number==unit:
                return i
        try:
            return int(number)
        except:
            return 4
    
    def _find_cuisine(self, food):
        cuisine = {"Vietnamese": 10675, "Sushi": 10653, "Asian": 10659, "Cafe": 10642, "Seafood": 10643, 
                    "European": 10654, "Bar": 10640, "International": 10648, "Italian": 4617, "Pizza": 10641, 
                    "Fast Food": 10646, "Pub": 10670, "French": 5086, "Steakhouse": 10345, "Healthy": 10679, 
                    "Barbecue": 10651, "Deli": 10666, "Russian": 10693, "American": 9908, "Eastern European": 10742, 
                    "Spanish": 10655, "British": 10662, "Fusion": 10671, "Soups": 10700, "Armenian": 10766, 
                    "Southwestern": 10634, "Thai": 10660, "Turkish": 10663, "Grill": 10668, "Diner": 10676, 
                    "Wine Bar": 10682, "Beer restaurants": 21355, "Mexican": 5110, "Chinese": 5379, "Japanese": 5473, 
                    "Indian": 10346, "Brew Pub": 10621, "Swiss": 10628, "Mediterranean": 10649, "Korean": 10661, 
                    "Gastropub": 10683, "Street Food": 10686, "Central European": 10746, "NorthWestern Chinese": 10780, 
                    "Arabic": 11744, "Fruit parlours": 21343, "Contemporary": 10669, "Singaporean": 10714, 
                    "Salvadoran": 10722, "South American": 10749, "Hong Kong": 10755, "Israeli": 10769
                    }

        if food is not None:
            for key, value in cuisine.items():
                if food.lower()==key.lower():
                    return value
        return None


class ActionSearchRestaurants(Action):
    def name(self):
        return "action_search_restaurants"

    def run(self, dispatcher, tracker, domain):

        print("Place:", tracker.get_slot("place"), "    People:", tracker.get_slot("people"),
                "\nFood:", tracker.get_slot("food"), "    Price:", tracker.get_slot("price") )

        restaurant_api = RestaurantAPI()
        res = restaurant_api.search(tracker)
        return [SlotSet("matches", res), SlotSet("counter", 0)]


class ActionSuggest(Action):
    def name(self):
        return "action_suggest_restaurant"

    def run(self, dispatcher: CollectingDispatcher, tracker, domain):

        options = tracker.get_slot("matches")
        msg = ""

        # If the user rejects our location, recommend another
        idx = tracker.get_slot("counter") 
        idx = int(idx)+1 if idx else 0
        
        if options:
            option = options[idx]
            
            # Extract location informations
            name = option["singleCardContent"]["cardTitle"]["string"]
            name_id = name.split(" ")[0] + " "
            name = name.replace(name_id, "")
            msg += str("'" + name + "'")
            
            if "primaryInfo" in option["singleCardContent"]:
                primaryInfo = option["singleCardContent"]["primaryInfo"]["text"].split(" • ")
                msg += str(" is a ")
                for i, info in enumerate(primaryInfo):
                    if i != 0:
                        msg = msg+info+" " if i+1==len(primaryInfo) else msg+info+", "
                msg += "restaurant."
                id = option["singleCardContent"]["saveId"]["id"]
            
            dispatcher.utter_message(text=msg)
            return [SlotSet("counter", str(idx))]
        else:
            dispatcher.utter_message(text="I'm sorry, the search did not return any results. Try changing something")
            return []


class ActionInformation(Action):
    def name(self):
        return "action_provide_informations"

    def run(self, dispatcher: CollectingDispatcher, tracker, domain):
        options = tracker.get_slot("matches")

        if options is not None:
            idx = tracker.get_slot("counter") 
            info = tracker.get_slot("info") 
            option = options[int(idx)]

            if "saveId" in option["singleCardContent"]:
                id = option["singleCardContent"]["saveId"]["id"]
            
            url = "https://travel-advisor.p.rapidapi.com/restaurants/get-details"
            querystring = {"location_id":id,"currency":"eur","lang":"en_US"}
            headers = {
                'x-rapidapi-host': "travel-advisor.p.rapidapi.com",
                'x-rapidapi-key': "ce62ea5053msh91c49554fdff0dap14f015jsn57264a71a9c7"
                }

            response = requests.request("GET", url, headers=headers, params=querystring)
            data = json.loads(response.text)
            location = data["location_string"] if "location_string" in data else None
            ranking = data["ranking"] if "ranking" in data else None
            #rating = data["rating"] if "rating" in data else None
            address = data["address_obj"]["street1"] if "address_obj" in data else None
            number = data["phone"] if "phone" in data else None

            msg = ""
            if info is None:
                msg += "The phone number is " + number + ". The restaurant is located in " + address + "."
            else:
                msg += "The phone number is " + number + "." if "number" in info or "phone" in info or "details" in info or "information" in info else ""
                msg += " The restaurant is located in " + address + (", in " + location if location else "") if "address" in info or "direction" in info or "location" in info or "information" in info or "details" in info else ""

            dispatcher.utter_message(text=msg)

        return []


class ActionGreet(Action):
    def name(self):
        return "action_greet"

    def run(self, dispatcher: CollectingDispatcher, tracker, domain):
        # SETTING GENDER AND AGE OF THE USER
        gender = tracker.get_slot("gender")
        age = tracker.get_slot("age")
        
        if gender is None or age is None:
            return [SlotSet("profile", 3)]

        profile = 1 if gender == "male" and age == "young" else 2 if gender == "female" and age == "young" else 3 if gender == "male" and age == "middle-aged" else 4 if gender == "female" and age == "middle-aged" else 5 if gender == "male" and age == "eldery" else 6
        return [SlotSet("profile", profile)]


'''
Queste due azioni servono solo per telegram
'''
class ActionGreet1(Action):
    def name(self):
        return "action_greet1"

    def run(self, dispatcher: CollectingDispatcher, tracker, domain):
        buttons = []
        buttons.append({"title": 'Male' , "payload": '/choose{"gender": "male"}'})
        buttons.append({"title": 'Female' , "payload": '/choose{"gender": "female"}'})
        dispatcher.utter_message(text= "What's your gender" , buttons=buttons)

        return []


class ActionGreet2(Action):
    def name(self):
        return "action_greet2"

    def run(self, dispatcher: CollectingDispatcher, tracker, domain):
        buttons = []
        buttons.append({"title": 'Young' , "payload": '/choose{"age": "young"}'})
        buttons.append({"title": 'Middle-aged' , "payload": '/choose{"age": "middle-aged"}'})
        buttons.append({"title": 'Eldery' , "payload": '/choose{"age": "eldery"}'})
        dispatcher.utter_message(text= "What's your age" , buttons=buttons)

        return []


  
