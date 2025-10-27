import requests
import os
import time
import threading

# --- SLACK configuration ---
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "") 
if SLACK_BOT_TOKEN == "":
    raise ValueError("Please replace SLACK_BOT_TOKEN with your real value from Slack App.")

SLACK_USER_IDS_LIST = ["YOUR_USER_ID_HERE"]  # Replace with actual user IDs
MESSAGE_TEXT_TEMPLATE = "Hello <@{}>! You have an IMPORTANT message from your NOC bot."
 
SPAM_COUNT = 3     # Number of repeated sends per user
DELAY_SECONDS = 3   # Delay between repeated sends (for the same user)

# --- Function to send a Slack message ---
def send_slack_direct_message(token, user_id, message_body):
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "channel": user_id,
        "text": message_body
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status() 
    response_data = response.json()
    return response_data.get("ok")

# --- Function to be run in each thread for each user ---
def send_messages_for_user(user_id, token, message_template, spam_count, delay):
    personal_message = message_template.format(user_id)
    print(f"--- [Thread for {user_id}] Start repeated sending ---")
    for i in range(spam_count):
        print(f"[Thread for {user_id}] Attempt {i+1}/{spam_count}: Sending message...")
        success = send_slack_direct_message(token, user_id, personal_message)
        if success:
            print(f"[Thread for {user_id}] Message sent successfully.")
        else:
            print(f"[Thread for {user_id}] Message sending FAILED (Slack returned ok=False).")
        if i < spam_count - 1:
            print(f"[Thread for {user_id}] Waiting {delay} seconds before next send...")
            time.sleep(delay)
    print(f"--- [Thread for {user_id}] Finished repeated sending ---\n")

# --- Main execution ---
if __name__ == "__main__":
    if SLACK_BOT_TOKEN == "xoxb-YOUR_TOKEN_HERE":
        print("Error: Please replace SLACK_BOT_TOKEN with your real value from Slack App.")
    elif not SLACK_USER_IDS_LIST:
        print("Error: SLACK_USER_IDS_LIST is empty. Please add User IDs.")
    else:
        threads = []
        print("Starting threads to send messages concurrently...\n")
        for user_id in SLACK_USER_IDS_LIST:
            # Create a new thread for each user
            thread = threading.Thread(
                target=send_messages_for_user, 
                args=(user_id, SLACK_BOT_TOKEN, MESSAGE_TEXT_TEMPLATE, SPAM_COUNT, DELAY_SECONDS)
            )
            threads.append(thread)
            thread.start() # Start thread
        # Wait for all threads to finish
        for thread in threads:
            thread.join() 
        print("\n--- All messages have been processed ---")