# OpenCode Discord Bot

This is a Discord bot that connects to OpenCode running in server mode.
If you really want to burn some tokens or just wipe your hard drive clean. You don't need Clawdbot/Moltbot.
This should take you less than 5 minutes to setup. 
## Setup

### 1. Start OpenCode Server

First, start OpenCode in server mode:

```bash
opencode serve --port 4096
```

Optionally, you can enable authentication:

```bash
OPENCODE_SERVER_PASSWORD=your_password opencode serve --port 4096
```

### 2. Configure Environment Variables

Create a `.env` file (or copy from `env_opencode.sample`):

```bash
cp env_opencode.sample .env
```

Edit `.env` and add your Discord bot token:

```env
DISCORD_TOKEN=your_discord_bot_token_here
OPENCODE_SERVER_URL=http://localhost:4096
OPENCODE_USERNAME=opencode
OPENCODE_SERVER_PASSWORD=your_password  # Optional
```

### 3. Install Dependencies

```bash
pip install -r requirements_opencode.txt
```

### 4. Run the Bot

```bash
python opencode_bot.py
```

## Usage

Once the bot is running, you can interact with it on Discord:

- **Send a message**: Just type your question or request (no prefix needed)
- **`!help`**: Show help information
- **`!session`**: Show current session ID
- **`!newsession`**: Create a new session
- **`!ping`**: Check bot latency

## How It Works

1. Each Discord user gets their own OpenCode session
2. Messages are sent to the OpenCode server API
3. Responses are retrieved and sent back to Discord
4. Session context is maintained for each user

## Features

- Session management per user
- Real-time communication with OpenCode
- Support for OpenCode authentication
- Simple command interface
- Automatic session creation

## API Endpoints Used

- `GET /global/health` - Check server health
- `GET /session` - List sessions
- `POST /session` - Create new session
- `POST /session/:id/message` - Send message to session

See [OpenCode Server Documentation](https://opencode.ai/docs/server/) for more details.
