import json
import logging
import os
import discord
import ffmpeg
from discord.ext import tasks
import tempfile
import subprocess

# NOTES FOR ABE:
# Added conversion.log to log ffmpeg conversion process and troubleshooting
# try to add conversion with link, I was unsuccessful because chatgpt sucks 10/05/2023


if os.path.exists(os.getcwd() + "/config.json"):

    with open("./config.json") as f:
        configData = json.load(f)

else:
    configTemplate = {"TOKEN": "", "Prefix": "!"}

    with open(os.getcwd() + "/config.json", "w+") as f:
        json.dump(configTemplate, f)

Token = configData["Token"]
Prefix = configData["Prefix"]

handler = logging.FileHandler(filename='conversion.log', encoding='utf-8', mode='w')

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f'Logged in as {client.user.name}')
    process_queue.start()


file_queue = []
file_channels = {}


@tasks.loop(seconds=5)
async def process_queue():
    if file_queue:
        # Get the first file in the queue
        file_path = file_queue.pop(0)

        # Print file_path to verify it's correct
        print(f'File path: {file_path}')

        # Extract the filename without extension
        file_name = os.path.splitext(os.path.basename(file_path))[0].replace('_input', '')

        try:
            # Check if the file exists
            if os.path.exists(file_path):
                output_path = f'output_{file_name.split("_")[0]}.mp4'

                # Process the file
                ffmpeg.input(file_path).output(f'output_{file_name}.mp4').run()

                # Send the converted file to the same channel
                channel_id = file_channels.get(file_path)
                if channel_id:
                    channel = client.get_channel(channel_id)
                    if channel:
                        await channel.send(file=discord.File(f'output_{file_path}'))
                    else:
                        print(f'Error: Channel with ID {channel_id} not found')
                else:
                    print('Error: Channel ID not found for the file')

                # Delete the files after sending
                os.remove(file_path)
                os.remove(output_path)
            else:
                print(f'File not found: {file_path}')
        except Exception as e:
            print(f'Error during video conversion: {e}')


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("!Hello Jarvis"):
        await message.channel.send("Hello Sir!")

    if message.content.startswith('!convert'):
        await message.channel.send("Converting, Please allow two minutes for the file to be processed!")
        if message.attachments:
            for attachment in message.attachments:
                if attachment.filename.endswith('.webm'):
                    # Create a temporary directory
                    with tempfile.TemporaryDirectory() as temp_dir:
                        input_path = os.path.join(temp_dir, f'input_{attachment.filename}')
                        output_path = os.path.join(temp_dir, 'output.mp4')

                        await attachment.save(input_path)

                        # Open the log file in append mode
                        log_file = open('conversion.log', 'a')

                        # Run ffmpeg command and redirect output to the conversion.log file
                        subprocess.run(['ffmpeg', '-i', input_path, output_path], stdout=log_file,
                                       stderr=subprocess.STDOUT)

                        # Close the log file
                        log_file.close()

                        # Send the converted file to the same channel
                        channel_id = message.channel.id
                        channel = client.get_channel(channel_id)
                        if channel:
                            await channel.send(file=discord.File(output_path))
                            print(f"File successfully converted and uploaded")
                        else:
                            print(f'Error: Channel with ID {channel_id} not found')

                        # Files in temp_dir are automatically deleted when the context ends

                else:
                    await message.channel.send(
                        f"Please send a webm file for conversion. Skipping '{attachment.filename}'.")

    if message.content.startswith('!delete'):
        async for msg in message.channel.history(limit=2):  # Get the last two messages
            if msg.author == client.user:  # Check if the message is from the bot
                if msg.attachments:
                    await message.channel.send("Right away Sir.")
                    if any(msg.attachments[0].url.endswith(ext) for ext in '.mp4'):
                        await msg.delete()  # Delete the bot's message
                break
            else:
                await message.channel.send("Nothing to be deleted Sir.")


logger = logging.getLogger('conversion')
logger.setLevel(logging.INFO)
logger.addHandler(handler)

client.run(Token)
