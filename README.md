# 6thBot

### Setup:

Before running anything, make sure you have the following packages installed via pip:
- discord.py (v1.3.2)
- pillow (v7.0.0)
- requests (v2.23.0)

Then, you'll need 3 API tokens:
- [discord](https://discordapp.com/developers/applications/) (Needed in order to run)
- [steam](https://steamcommunity.com/dev/apikey) (Needed for the `steam` command in `apis.py`)
- [giphy](https://developers.giphy.com/dashboard/) (Needed for the `gif` command in `apis.py`)

Replace the placeholder tokens in `json/api_keys_default.json`, and rename the file to `api_keys.json`.
The main entry point of the script is `main.py`.

### Misc:

Making a new module? Make sure to add `bot.load_extension(fileName)` at the end of `main.py`.
