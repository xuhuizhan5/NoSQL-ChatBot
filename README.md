# NoSQL Final Project

**Author: Xuhui Zhan**

**Email: xuhui.zhan@vanderbilt.edu**

[Download Video Demonstration](fp_daniel_demo.mp4)

## Project Introduction

This final project is an extension of my **Mini Project 1: Redis Chatbot**, where I built a chatbot leveraging Redis, API integrations, and prompt engineering with OpenAI's language model. Recognizing the potential for further exploration and enhancement, I decided to continue working on the project. The goal is to expand its functionality and refine its capabilities, making it more robust and versatile for real-world applications.

The chatbot integrates real-time features such as multi-channel communication, weather and stock data retrieval, and advanced tone-mimicking through prompt engineering. It also utilizes Redis' **pub/sub** mechanism for efficient message broadcasting and its versatile data structures for managing chat history, user sessions, and dynamic updates.

### Why Redis?

Redis was chosen for this project due to its unique strengths that align with the chatbot's requirements:

1. **Real-Time Performance**:

   - Redis' in-memory architecture ensures lightning-fast read and write operations, which is essential for handling real-time chat messages and updates.
2. **Pub/Sub Mechanism**:

   - Redis' **publish/subscribe** system allows seamless message broadcasting across multiple channels, making it ideal for a multi-channel chatbot.
3. **Versatile Data Structures**:

   - Redis supports diverse data types, such as strings, lists, and sets, which are used to store and manage chat messages, user subscriptions, and command history efficiently.
4. **Dynamic Data Management**:

   - With Redis' **TTL (time-to-live)** feature, data like weather updates can expire automatically, ensuring only the most recent information is stored.
5. **Scalability and Simplicity**:

   - Redis is lightweight, easy to set up, and scales well with increasing user interactions and data volume, making it a practical choice for this project.

By continuing to work on this chatbot, I aim to unlock its full potential and explore Redis' capabilities further, creating a scalable, efficient, and user-friendly system.

## Usage

1. Make sure you have docker server running, by runing `docker ps` if there is valid output
2. Modify the line 18 in the `docker.yml`, replace the path `/Users/xuhuizhan/homework/NoSQL/mini_project` by your corresponding path of the folder containing both the `docker.yml` and `mp1_chatbot.py`
3. Open a terminal, navigate to the current folder and run `docker compose up` (This command is for Mac which is the development platform, for other platform, there are similar commands like `docker-compose up`)
4. Open a `<u>`new `</u>` terminal, navigate to the current folder and run `docker compose exec -it python-app bash`
5. Within the latest terminal, run `pip install -r requirements.txt`
6. Also make sure you have the `api_key.json` completed by using `api_key_template.json`, by given you OPENAI_API key from https://platform.openai.com/docs/overview and owm_api_key from https://www.weatherapi.com/
7. Within the latest terminal, run `python fp_chatbot.py` and then you could start to chat!

## At the very beginning

The program will fetch stock history from 2024-01-01 till today for the pre-set companies from Yahoo finance and save the relevant data to redis database.

## Instructions on commands and options

### Commands

`!help`: List all the commands as

`!weather <city>`: Replace the `<city>` with the city you would like to update, it would output the city weather if there is data existed, if not it would try to fetch data from open weather api, else it would instructed you the available options. The data would always be most recent and updated when

`!stock` You could then input the interested company, the chatbot would then plot the stock price for saved data related to the interested company if exists in database.

`!fact` Output the random fact about the chatbot

`!whoami` Output the user information of current user you identified

`!4` Send a message anonymously, the message will have a username as Anonymous

### Options

`1` Identify the current user

`2` Join a channel, if you haven' t identify yourself using option `1`, it would ask you to do first, you would need to specified the name you would like to join first.

After you join, it will:

1. Send a message to the channel you join to indicate you are joined with the username identified before
2. Listen to the specific channel, and output messages from it. (By threading, during the listening, you could still type)
3. Based on what you type:

`!history`: Show the chat history of this channel (Only contains the ones being successfully subscribed)

`!leave`: Leave the channel and stop the listenning thread.

`!mimic tone`: Chatbot will mimic a specific user' s tone based on the chatting history of current channel, by leveraging openai api and prompt engineering (The user to mimic should be a real user in the history or in system, the user info would be given to gpt for better mimicking). (You could type `!leave` to return to channel instead of chat with the bot mimicing a user)

Other messages: Directly sent to the current channel

`3` Leave a channel, it would delete the channel you subscribe in the redis database, which record what channels specific user join as a set for each user. Users listenning to the channel would receive a message indicating you left.

`4` Send a message to a channel

`5` Get information about a user

`6` Exit the chat room, which will close the program

`7` Listen to channels by pattern, any channel have this kind of pattern would be subsribed and output the messages.

## Database related queries

1. Set value by key
2. Set value by key and expiration time
3. Fetch value by key
4. Fetch a set by key
5. Add value to a set by key and value
6. Subsribe to a channel
7. Publish messages to a channel
8. Unsubscribe from a channel
9. Set a list by key
10. Add a value to a list by key and value
11. Etc..

## What makes it special

1. A new option as `7` to listen to multiple channels by patterns
2. `!weather` that could try to fetch data from open weather api if not existed, it will also show yesterday' s weather if saved
3. A new command as `!4` to send messages annoymously
4. Multi-thread desgins with special commands as `!history` and `!leave` enabling to publish message while listening
5. Special `!history` command is enabled by saving history messages into a list with designed key
6. Special `!mimic tone` command by leveraging openai api and prompt engineering
7. Special `!stock` that would plot the history price for interested company directly in terminal

## Challenges and How They Were Addressed

#### 1. Integrating Real-Time Data

- **Challenge**: Ensuring accurate and up-to-date data for weather and stock information, plot in terminal
- **Solution**: Checked Redis for existing data, fetched updates from APIs if missing, and stored the results back in Redis, use plotext to enable ploting the price change in terminal directly.

#### 2. Enabling Multi-Threaded Communication

- **Challenge**: Allowing users to listen to channels and interact without interruption.
- **Solution**: Added threading to support simultaneous channel listening and command execution. Set timeout for listening event to ensure smooth interruption.

#### 3. Managing Redis Data Efficiently

- **Challenge**: Handling large volumes of data for channels, messages, and user interactions.
- **Solution**: Designed Redis schemas with clear structures for storing and retrieving sets, lists, and keys with expiration policies.

#### 4. Ensuring Recent Weather Data Storage

- **Challenge**: Storing only the most recent weather data without overwriting or holding stale data.
- **Solution**: Calculated the time-to-live (TTL) dynamically using `datetime` by determining the seconds until midnight. Integrated this into the Redis storage mechanism to adjust the TTL dynamically for each weather update.

#### 5. Using OpenAI for Tone Mimicking

- **Challenge**: Generating chatbot responses that mimic user tones based on chat history.
- **Solution**: Leveraged OpenAI’s API with carefully crafted prompts to achieve consistent and relevant tone mimicking.

#### 6. User-Friendly Commands and Interactivity

- **Challenge**: Providing a range of functionalities without overwhelming the user.
- **Solution**: Developed clear commands like `!weather`, `!stock`, and `!mimic tone`, ensuring documentation was easy to follow.

## Summary

The **NoSQL Final Project** is a chatbot that combines data scraping, API calls, Redis database operations, and OpenAI’s language model to create a functional and interactive system. It allows users to fetch weather updates, plot stock prices, send messages (including anonymously), and mimic user tones based on chat history. Multi-threading ensures smooth real-time interactions in chatrooms, letting users send messages and execute commands simultaneously. Redis is used to store and manage chat history, user data, and channel subscriptions efficiently.

The project stands out with features like dynamic weather and stock data fetching, multi-channel listening based on patterns, and the ability to mimic user tones using OpenAI’s API and prompt engineering. It offers a practical and responsive system for communication and data management.
