# Discord Moderation Bot

A Discord moderation bot built with discord.py, using the `.` prefix.

## Run & Operate

- The **Discord Bot** workflow runs the bot automatically.
- `python3 bot/bot.py` — run the bot manually from the shell.
- Warnings are persisted to `bot/warnings.json`.

## Stack

- Python 3.13, discord.py 2.x
- Prefix: `.`
- Required secret: `DISCORD_TOKEN`

## Commands

| Command | Permission | Description |
|---|---|---|
| `.help [command]` | Everyone | Show all commands or details for one |
| `.ban @user [reason]` | Ban Members | Permanently ban a member |
| `.kick @user [reason]` | Kick Members | Kick a member |
| `.mute @user [duration] [reason]` | Moderate Members | Timeout a member (e.g. `10m`, `2h`, `1d`) |
| `.unmute @user [reason]` | Moderate Members | Remove a timeout |
| `.warn @user [reason]` | Kick Members | Warn a member (persisted to JSON) |
| `.warnings @user` | Kick Members | List warnings for a member |
| `.clearwarns @user` | Kick Members | Clear all warnings for a member |
| `.pex @user <role name>` | Manage Roles | Give a role to a member |
| `.depex @user <role name>` | Manage Roles | Remove a role from a member |
| `.clear [amount] [@user]` | Manage Messages | Bulk-delete messages (default: 10) |
| `.lock [#channel] [reason]` | Manage Channels | Lock a channel for @everyone |
| `.unlock [#channel] [reason]` | Manage Channels | Unlock a channel |
| `.say [#channel] <message>` | Manage Messages | Send a plain message as the bot |
| `.embed [#channel] "Title" <desc>` | Manage Messages | Send an embed as the bot |

## Where things live

- `bot/bot.py` — all bot logic
- `bot/warnings.json` — persisted warning records (auto-created)
- `bot/requirements.txt` — Python dependencies

## User preferences

_Populate as you build._
