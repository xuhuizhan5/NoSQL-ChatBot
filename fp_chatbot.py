import redis
import json
import re
import threading
from pyowm import OWM
from datetime import datetime, timedelta
import yfinance as yf
import openai
import pandas as pd
import plotext as plt
from io import StringIO

class RedisChatBot:
    def __init__(self, bot_name:str = "Redis", host:str='my-redis', port:int=6379)->None:
        self.client = redis.Redis(host=host, port=port)
        self.pubsub = self.client.pubsub()
        self.bot_name = bot_name
        self.current_user = None
        self.client.set("fun_fact", "I'm a Redis Chatbot. I might be a homework assignment but I'm still fun!")
        self.tickers = ["AAPL", "GOOGL", "AMZN", "MSFT", "TSLA", "FB", "NVDA", "PYPL", "INTC", "ADBE"]
        now = datetime.now()
        now_str = now.strftime("%Y-%m-%d")
        midnight = datetime(now.year, now.month, now.day) + timedelta(days=1)
        # Yesterday's weather will remain until today
        yesterday = now - timedelta(days=1)
        yesterday_str = yesterday.strftime("%Y-%m-%d")
        ttl = int((midnight - now).total_seconds())
        self.client.setex(f"weather:Nashville:{yesterday_str}", ttl, json.dumps({"weather": "Cloudy"}))
        
        # Today' s weather will remain until the day after tomorrow
        ttl = int((midnight - now).total_seconds()) + 24 * 60 * 60
        self.client.setex(f"weather:New York:{now_str}", ttl, json.dumps({"weather": "Sunny"}))
        self.client.setex(f"weather:San Francisco:{now_str}", ttl, json.dumps({"weather": "Foggy"}))
        self.client.setex(f"weather:Los Angeles:{now_str}", ttl, json.dumps({"weather": "Cloudy"}))
        self.client.setex(f"weather:Nashville:{now_str}", ttl, json.dumps({"weather": "Rainy"}))
        # Initialize threading components
        self.channel_threads = {}
        self.stop_events = {}
        
        try:
            # Initialize OWM, read api key from owm_api_key.json
            with open('api_key.json') as f:
                dict = json.load(f)
                owm_api_key = dict['owm_api_key']
            owm = OWM(owm_api_key)
            self.mgr = owm.weather_manager()
        except FileNotFoundError:
            print("owm_api_key.json not found. Please add the file with the OWM API key.")
            return

        # Fetch stock prices
        self.fetch_stock_price()

    def fetch_stock_price(self):
        start_date = "2024-01-01"
        now = datetime.now()
        end_date = now.strftime("%Y-%m-%d")
        for ticker in self.tickers:
            try:
                print(f"Fetching data for {ticker}...")
                # Fetch historical data
                stock = yf.Ticker(ticker)
                historical_data = stock.history(start=start_date, end=end_date)

                # Convert to JSON for Redis storage
                historical_data_json = historical_data.to_json()
                # print(ticker)
                # print(historical_data_json)

                # Store in Redis (key = ticker)
                ticker_key = f"stock:{ticker}"
                self.client.set(ticker_key, json.dumps(historical_data_json))
                print(f"Data for {ticker} saved in Redis.")
            except Exception as e:
                print(f"Error fetching data for {ticker}: {e}") 

    def list_command(self):
        print(f"\tHere are the commands you can use:")
        print(f"\t!help: List of commands")
        print(f"\t!weather <city>: Weather update")
        print(f"\t!fact: Random fact")
        print(f"\t!whoami: Your user information")
        print(f"\t!4: Send a message anonymously")
        print(f"\t!stock: Get stock price from database and plot")

    def list_options(self):
        print("\n\nOptions:")
        print("1: Identify yourself")
        print("2: Join a channel")
        print("3: Leave a channel")
        print("4: Send a message")
        print("5: Get info about a user")
        print("6: Exit")
        print("7: Listen to multiple channels by pattern")

    def identify_user(self):
        user_name = input("Enter your username: ")
        if user_name == "System":
            print("Invalid username. Please try again.")
            self.identify_user()
            return
        user_age = input("Enter your age: ")
        user_gender = input("Enter your gender:")
        user_location = input("Enter your location:")

        # Check if all the fields are filled
        if not user_name or not user_age or not user_gender or not user_location:
            print("You haven't filled all the fields. Please try again.")
            return

        user_key = f"user:{user_name}"
        self.client.hset(user_key, mapping={
            "user_name": user_name,
            "user_age": user_age,
            "user_gender": user_gender,
            "user_location": user_location
        })

        self.current_user = user_name

    def join_channel(self, channel_name:str):
        channels_key = f"channels: {self.current_user}"
        self.client.sadd(channels_key, channel_name)
        self.send_a_message(channel_name, f"User {self.current_user} has joined the channel.")

        # Start listening in a separate thread with a stop event
        stop_event = threading.Event()
        listen_thread = threading.Thread(target=self.listen_to_channel, args=(channel_name, stop_event))
        listen_thread.daemon = True
        listen_thread.start()

        # Store the thread and event so we can stop it later
        self.channel_threads[channel_name] = listen_thread
        self.stop_events[channel_name] = stop_event

    def leave_channel(self, channel_name:str):
        channels_key = f"channels: {self.current_user}"
        self.client.srem(channels_key, channel_name)
        self.send_a_message(channel_name, f"User {self.current_user} has left the channel.")

        print(f"Leaving channel {channel_name}")

        # Stop the listening thread
        if channel_name in self.stop_events:
            print(f"Stopping listening to {channel_name}")
            self.stop_events[channel_name].set()
            print(f"Waiting for the thread to finish...")
            # Wait for the thread to finish
            self.channel_threads[channel_name].join()
            print(f"Thread finished.")
            del self.stop_events[channel_name]
            del self.channel_threads[channel_name]
        else:
            print(f"Not listening to {channel_name}")
        print(f"Left channel {channel_name}")

    def send_a_message(self, channel_name:str, message:str, user_name:str="System"):
        message = json.dumps({
            "username": user_name,
            "message": message
        })
        self.client.publish(channel_name, message)
        # Append the message to the Redis list for history
        history_key = f"channel:{channel_name}:history"
        self.client.rpush(history_key, message)

    # def listen_to_channel(self, channel_name:str, stop_event):
    #     pubsub = self.client.pubsub()
    #     pubsub.subscribe(channel_name)
    #     print(f"Listening to {channel_name}. Type '!history' to see chat history, '!leave' to leave the channel. !mimic tone to mimic the tone of a user.")
    #     for message in pubsub.listen():
    #         if stop_event.is_set():
    #             print(f"Stopped listening to {channel_name}")
    #             break
    #         if message['type'] == 'message':
    #             msg_data = message['data'].decode('utf-8')
    #             print(f"Message from {channel_name}: {msg_data}")

            
    #     pubsub.unsubscribe()
    #     pubsub.close()
    #     print("Return back to the main menu.")

    def listen_to_channel(self, channel_name: str, stop_event):
        pubsub = self.client.pubsub()
        pubsub.subscribe(channel_name)
        print(f"Listening to {channel_name}. Type '!history' to see chat history, '!leave' to leave the channel, '!mimic tone' to mimic the tone of a user.")
        
        try:
            while not stop_event.is_set():
                message = pubsub.get_message(timeout=2)  # Non-blocking with a timeout
                if message:
                    if message['type'] == 'message':
                        msg_data = message['data'].decode('utf-8')
                        print(f"Message from {channel_name}: {msg_data}")
        finally:
            pubsub.unsubscribe()
            pubsub.close()
            print("Return back to the main menu.")

    def get_user_info(self, user_name:str):
        user_key = f"user:{user_name}"
        user_info = self.client.hgetall(user_key)
        user_info = {key.decode('utf-8'): value.decode('utf-8') for key, value in user_info.items()}
        if user_info:
            print(f"User Name: {user_info.get('user_name')}")
            print(f"User Age: {user_info.get('user_age')}")
            print(f"User Gender: {user_info.get('user_gender')}")
            print(f"User Location: {user_info.get('user_location')}")
        else:
            print(f"User {user_name} not found.")

    def join_multiple_channels_by_pattern(self, pattern:str):
        self.pubsub.psubscribe(pattern)

        # Send a message to all the channels
        for channel_name in self.client.pubsub_channels():
            self.send_a_message(channel_name, f"User {self.current_user} has joined the channel.")
        
        # Listen to all the channels
        for message in self.pubsub.listen():
            if message['type'] == 'pmessage':
                msg_data = message['data'].decode('utf-8')
                channel_name = message['channel'].decode('utf-8')
                print(f"Message from {channel_name}: {msg_data}")

    def get_weather(self, city:str):
        now = datetime.now()
        now_str = now.strftime("%Y-%m-%d")

        # Check if we have weather data for yesterday, it is ok if we don't
        yesterday = now - timedelta(days=1)
        yesterday_str = yesterday.strftime("%Y-%m-%d")
        yesterday_weather_key = f"weather:{city}:{yesterday_str}"
        yesterday_weather_data = self.client.get(yesterday_weather_key)
        if yesterday_weather_data:
            yesterday_weather_data = json.loads(yesterday_weather_data)
            print(f"Weather in {city} yesterday: {yesterday_weather_data.get('weather')}")
        
        weather_key = f"weather:{city}:{now_str}"
        weather_data = self.client.get(weather_key)
        if weather_data:
            weather_data = json.loads(weather_data)
            print(f"Weather in {city} today: {weather_data.get('weather')}")
        else:
            # Try to get weather data from the API if not found in Redis
            try:
                self.get_weather_from_api(city)
            except:
                print(f"Weather data for {city} not found.")
                self.list_available_cities()



    def get_weather_from_api(self, city:str):
        # The city name should be in the format "city,US"
        search_city = f'{city},US'

        observation = self.mgr.weather_at_place(search_city)
        weather = observation.weather
        weather_data = {
            "weather": weather.detailed_status
        }

        now = datetime.now()
        midnight = datetime(now.year, now.month, now.day) + timedelta(days=1)
        # Today' s weather will remain until the day after tomorrow
        ttl = int((midnight - now).total_seconds()) + 24 * 60 * 60

        now_str = now.strftime("%Y-%m-%d")
        weather_key = f"weather:{city}:{now_str}"
        self.client.setex(weather_key, ttl, json.dumps(weather_data))

        print(f"Weather in {city} today: {weather_data.get('weather')}")

    def list_available_cities(self):
        # Fetch all keys matching the pattern "weather.*"
        keys = self.client.keys(f"weather:*")
        keys = [key.decode('utf-8') for key in keys]

        # Extract city names from the keys
        cities_time = [key.split("weather:")[1] for key in keys]
        cities = [city_time.split(":")[0] for city_time in cities_time]
        # Remove duplicates
        cities = list(set(cities))

        if cities:
            print("Available cities in database:")
            for city in cities:
                print(city)
        else:
            print("No cities available")

    def fun_fact(self):
        fun_fact = self.client.get("fun_fact")
        print(f"Some fun facts about me: {fun_fact}")

    def show_channel_history(self, channel_name:str):
        history_key = f"channel:{channel_name}:history"
        messages = self.client.lrange(history_key, 0, -1)
        print(f"Chat history for {channel_name}:")
        for msg in messages:
            print(msg.decode('utf-8'))

    def mimic_tone(self, channel_name:str):
        history_key = f"channel:{channel_name}:history"
        messages = self.client.lrange(history_key, 0, -1)
        # Convert all the messages to a string for later use
        messages = [msg.decode('utf-8') for msg in messages]
        # Convert the list to a string
        chat_history_str = "\n".join(messages)
        option = input("Enter the username to mimic the tone: ")
        # Get user info by username
        user_key = f"user:{option}"
        user_info = self.client.hgetall(user_key)
        user_info = {key.decode('utf-8'): value.decode('utf-8') for key, value in user_info.items()}
        if not user_info:
            print(f"User {option} not found.")
            return
        else:
            user_str = f"User Name: {user_info.get('user_name')}, User Age: {user_info.get('user_age')}, User Location: {user_info.get('user_location')}"
        conversation = [
            {"role": "system", "content": f"You are a chatbot that continues conversations by mimicking the tone and style of {option} based on the existing chat history and User information for {option} as {user_str}."},
            {"role": "user", "content": f"Here is the chat history for context:\n{chat_history_str}"},
        ]

        print(f"Started to mimic the tone of {option}. Type '!leave' to stop.")
        while True:
            user_input = input('You: ')
            if user_input == '!leave':
                print("Stopped mimicking the tone.")
                print("Welcome back to the normal chat!")
                break
             # Add user's input to the conversation
            conversation.append({"role": "user", "content": user_input})

            # Call the OpenAI Chat API
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",  # Use "gpt-4" if available
                    messages=conversation,
                    temperature=0.7,
                    max_tokens=150,
                )
                # Extract the assistant's reply
                bot_reply = response['choices'][0]['message']['content'].strip()

                # Add bot's reply to the conversation
                conversation.append({"role": "assistant", "content": bot_reply})

                # Print the bot's reply
                print(f"Bot mimicing {option}: {bot_reply}")

            except Exception as e:
                print(f"Error: {e}")
                break
        

    def get_stock_price(self, ticker:str):
        ticker_key = f"stock:{ticker}"
        historical_data_json = self.client.get(ticker_key)
        if historical_data_json:
            historical_data_json = json.loads(historical_data_json)
            data_df = pd.read_json(StringIO(historical_data_json))
            plt.clear_figure()
            plt.date_form('Y-m-d H:M:S')
            dates = data_df.index
            close_prices = data_df['Close'].to_list()
            dates = plt.datetimes_to_string(dates)
            plt.plot(dates, close_prices)
            plt.title(f"{ticker} Stock Price History")
            plt.xlabel("Date")
            plt.ylabel("Stock Price $")
            plt.show()
        else:
            print(f"Stock data for {ticker} not found.")
            print(f"Avaliable tickers: {self.tickers}")



    def start_chat_with_clients(self):
        print(f"\n\tHello! I'm your friendly {self.bot_name} Chatbot.")
        self.list_command()
        while True:
            # List the options at the beginning
            self.list_options()
            option = input("Enter your choice: ")
            pattern = r"!weather ([a-zA-Z]+)"
            match = re.match(pattern, option)
            if match:
                city = match.group(1)
                self.get_weather(city)

            elif option == '1':
                self.identify_user()

            elif option == '!stock':
                ticker = input("Enter the stock ticker: ")
                self.get_stock_price(ticker)

            elif option == '2':
                if not self.current_user:
                    print('\033[1m' + "You need to identify yourself first." + '\033[0m')
                    # print("You need to identify yourself first.")
                    continue
                channel_name = input("Enter the channel name to join: ")
                self.join_channel(channel_name)
                # Enter channel loop
                while True:
                    user_input = input()
                    if user_input == '!history':
                        self.show_channel_history(channel_name)
                    elif user_input == '!leave':
                        self.leave_channel(channel_name)
                        print("Welcome back to the main menu!")
                        break
                    elif user_input == '!mimic tone':
                        self.mimic_tone(channel_name)
                    else:
                        # Send the message to the channel
                        username = self.current_user
                        self.send_a_message(channel_name, user_input, username)

            elif option == '3':
                channel_name = input("Enter the channel name to leave: ")
                self.leave_channel(channel_name)

            elif option == '4':
                channel_name = input("Enter the channel name: ")
                message = input("Enter your message: ")
                username = self.current_user
                self.send_a_message(channel_name, message, username)

            elif option == '5':
                username = input("Enter username to get info about: ")
                self.get_user_info(username)

            elif option == '6':
                print("Exiting...")
                return

            elif option == '7':
                pattern = input("Enter the pattern to join multiple channels: ")
                self.join_multiple_channels_by_pattern(pattern)

            elif option == '!help':
                self.list_command()

            elif option == '!fact':
                self.fun_fact()

            elif option == '!whoami':
                print(f"Current User: {self.current_user}")
                self.get_user_info(self.current_user)

            elif option == '!4':
                channel_name = input("Enter the channel name: ")
                message = input("Enter your message: ")
                self.send_a_message(channel_name, message, "Anonymous")

            else:
                print("Invalid option. Please try again.")

if __name__ == '__main__':
    with open('api_key.json') as f:
        dict = json.load(f)
        openai_api_key = dict["OPENAI_API_KEY"]

    openai.api_key = openai_api_key
    redis_chatbot = RedisChatBot()
    redis_chatbot.start_chat_with_clients()