# BaselHack Ticket Checker Bot

This is a Python-based Telegram bot that periodically checks the [BaselHack Shop](https://www.baselhack.ch/shop) for ticket availability. If tickets are found, it sends a notification to a specified Telegram chat and an email to a configured address.

## Features

- **Automated Checking**: Periodically checks for tickets using an async architecture.
- **Telegram Integration**: Control the bot and receive status updates via Telegram commands.
- **Email Notifications**: Get an email notification the moment tickets become available.
- **Systemd Service**: Includes a `systemd` service file for easy deployment on a Linux server.
- **Configurable**: All settings are managed through a `.env` file.

## Prerequisites

- Python 3.8+
- A Telegram Bot Token (get one from [BotFather](https://t.me/BotFather))
- Your Telegram Chat ID (you can get it from a bot like [@userinfobot](https://t.me/userinfobot))
- An email account (e.g., Gmail) to send notifications from.

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd basel-hack-ticket-bot
    ```

2.  **Create a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure environment variables:**
    Create a file named `.env` in the project root and add the following content. **Fill in your actual credentials.**

    ```ini
    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
    TELEGRAM_CHAT_ID="YOUR_TELEGRAM_CHAT_ID"

    # Checker Configuration
    CHECK_INTERVAL_SECONDS=1200 # Default check interval in seconds (e.g., 1200 for 20 minutes)
    TARGET_URL="https://www.baselhack.ch/index.php?p=actions/sprig-core/components/render&sprig%3Aconfig=de1263fa40f93733713fe33b328388ebf8598d21ac75f3a0c817ef386a8d91a1%7B%22id%22%3A%22ticket%22%2C%22siteId%22%3A2%2C%22template%22%3A%22_components%5C%2Fsprig%5C%2Fproduct.twig%22%2C%22variables%22%3A%7B%22productId%22%3A13662%7D%7D"

    # Email Notification Configuration (for when tickets are found)
    EMAIL_HOST="smtp.gmail.com" # Example for Gmail
    EMAIL_PORT=587
    EMAIL_USE_TLS=True
    EMAIL_HOST_USER="your_email@gmail.com"
    EMAIL_HOST_PASSWORD="your_gmail_app_password" # Use an App Password for Gmail
    EMAIL_RECIPIENT="recipient_email@example.com"
    ```
    **Note on Gmail:** If you are using a Gmail account to send emails, you'll need to generate an "App Password" for this bot. You can find instructions on how to do that [here](https://support.google.com/accounts/answer/185833).

## Usage

### Running the Bot Directly

To run the bot directly from your terminal (for testing or development):

```bash
source venv/bin/activate
python bot.py
```

### Running as a Systemd Service (for Production)

To run the bot as a persistent background service on a Linux server:

1.  **Edit the service file:**
    Open `basel-hack-ticket-bot.service` and replace the placeholder values with your actual user, group, and project path.

    -   `User=your_user`
    -   `Group=your_group`
    -   `WorkingDirectory=/path/to/your/basel-hack-ticket-bot`
    -   `ExecStart=/path/to/your/basel-hack-ticket-bot/venv/bin/python bot.py`

2.  **Install and start the service:**
    ```bash
    # Move the service file to the systemd directory
    sudo cp basel-hack-ticket-bot.service /etc/systemd/system/

    # Reload the systemd daemon to recognize the new service
    sudo systemctl daemon-reload

    # Enable the service to start on boot
    sudo systemctl enable basel-hack-ticket-bot.service

    # Start the service immediately
    sudo systemctl start basel-hack-ticket-bot.service
    ```

3.  **Check the service status:**
    You can check if the service is running correctly with:
    ```bash
    sudo systemctl status basel-hack-ticket-bot.service
    ```
    And view its logs with:
    ```bash
    sudo journalctl -u basel-hack-ticket-bot -f
    ```

## Telegram Bot Commands

Once the bot is running, you can interact with it in your configured Telegram chat:

-   `/start [interval]`
    Starts the periodic checks. You can optionally provide an interval in seconds. If not provided, it uses the `CHECK_INTERVAL_SECONDS` from the `.env` file.
    *Example:* `/start 300` (checks every 5 minutes)

-   `/stop`
    Stops the periodic checks.

-   `/check`
    Triggers an immediate, one-time check for ticket availability.

---
*Disclaimer: This bot is for educational purposes. Please use it responsibly and respect the website's terms of service.*
