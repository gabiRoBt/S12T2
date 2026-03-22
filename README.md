<div align="center">
<pre>
_____/\\\\\\\\\\\________/\\\____/\\\\\\\\\______/\\\\\\\\\\\\\\\____/\\\\\\\\\_____        
 ___/\\\/////////\\\__/\\\\\\\__/\\\///////\\\___\///////\\\/////___/\\\///////\\\___       
  __\//\\\______\///__\/////\\\_\///______\//\\\________\/\\\_______\///______\//\\\__      
   ___\////\\\_____________\/\\\___________/\\\/_________\/\\\_________________/\\\/___     
    ______\////\\\__________\/\\\________/\\\//___________\/\\\______________/\\\//_____    
     _________\////\\\_______\/\\\_____/\\\//______________\/\\\___________/\\\//________   
      __/\\\______\//\\\______\/\\\___/\\\/_________________\/\\\_________/\\\/___________  
       _\///\\\\\\\\\\\/_______\/\\\__/\\\\\\\\\\\\\\\_______\/\\\________/\\\\\\\\\\\\\\\_ 
        ___\///////////_________\///__\///////////////________\///________\///////////////__
</pre>
  
  <h1>Advanced Chatbot Automation</h1>
  <p>A complex automation system based on Playwright and Discord for intelligent management of Facebook Messenger and Instagram Direct conversations using the Cohere API.</p>
</div>

---

## 🤖 Features

- **Multi-Platform Support:** Automates conversations seamlessly across both Facebook and Instagram.
- **Discord Orchestration:** Control the entire system directly from Discord via Slash (`/`) commands and fetch targets from dedicated text channels.
- **Human Behavior Simulation:** Bypasses bot detection with realistic reading delays, character-by-character typing, and natural mouse/scroll movements while respecting a daily sleep/activity schedule.
- **Memory & Profiling:** Automatically extracts and saves user details (name, age, job, relationship status, mood) to a local SQLite database (`profiles.db`) for highly contextualized responses.
- **AI Personalities:** Responses are driven by system prompts that define the bot's persona (e.g., affectionate friend, coworker, broken English speaker).
- **Persistent Sessions:** Saves browser states (`session_fb.json`, `session_ig.json`) to bypass repetitive logins and security alerts.

## 🚀 Installation

1. Install the required Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Install the necessary Playwright browsers:
   ```bash
   playwright install chromium
   ```
3. Set up your environment variables by copying the template:
   ```bash
   cp .env.example .env
   ```

> **Note:** Ensure you fill out the `.env` file with your Discord token, Cohere API key, and social media credentials before running the bot.

## 💻 Usage

Start the main entry point to initialize the bot and launch the Discord listener:

```bash
python main.py
```

*Once online, use your designated Discord channels (`facebook-ids` and `instagram-ids`) to feed target IDs to the bot. Add one ID per line, optionally followed by the desired persona separated by a `|`.*

**Target Channel Example:**
```text
987654321 | amic
123456789 | iubita
111222333 | englez_stalcit
444555666              # Lines without a persona use the default
```

## 👾 Discord Commands

Control the bot directly from your Discord server using the following Slash commands:

| Command | Action | Description |
|---------------|--------|-------------|
| `/run`  | **Start Flow** | Starts the normal processing flow for all IDs, respecting the human-like schedule. |
| `/alwaysonline`  | **Force Active** | Ignores the sleep/activity schedule and responds to all messages in under 1 minute. |
| `/test <platform> <id>`  | **Debug Target** | Runs the bot strictly for a single account. Great for debugging. |
| `/personalitati`  | **List Personas** | Displays a list of all available AI personalities defined in the code. |
| `/demo [persona]`  | **Test in DM** | Starts a simulated test session directly in your Discord DMs. |
| `/stopdemo`  | **End Test** | Stops the active DM demo session. |

## ⚙️ Configuration Options

Customize your bot's behavior by editing the following core files:

| Option | Description |
|--------|-------------|
| **`.env` Settings** | Configure your Discord Token, Cohere API Key, Facebook/Instagram credentials, and the exact names of your target Discord channels. |
| **`personalities.py`** | Add new personas to the `PERSONALITIES` dictionary by defining a `name` and a `prompt` (e.g., "Fitness Coach: You respond with short, motivational fitness quotes"). |
| **`profiles.db`** | The local SQLite database where all extracted contextual data for your targets is stored and managed. |

## 🚨 Requirements

- Python 3.8+
- `discord.py`, `playwright`, `httpx`, `cohere`
- Active Discord Bot Token & Server
- Cohere API Key
- Valid Facebook and Instagram accounts

> **Disclaimer:** This project is for educational and entertainment purposes only. Automating user accounts on platforms like Facebook and Instagram may violate their Terms of Service (ToS) and result in account suspension. Use responsibly.

---
---
---

<div align="center">
<pre>
   ...     ..      ..          ..                    ....                ..      .     
 x*8888x.:*8888: -"888:     :**888H: `: .xH""      .xH888888Hx.          x88f` `..x88. .> 
 X   48888X `8888H  8888     X   `8888k XX888      .H8888888888888:      :8888   xf`*8888%  
X8x.  8888X  8888X  !888>  '8hx  48888 ?8888      888*"""?""*88888X    :8888f .888  `"`   
X8888 X8888  88888   "*8%- '8888 '8888 `8888     'f     d8x.   ^%88k  88888' X8888. >"8x  
'*888!X8888> X8888  xH8>    %888>'8888  8888    '>    <88888X   '?8  88888  ?88888< 888> 
  `?8 `8888  X888X X888>     "8 '888"  8888      `:..:`888888>    8> 88888   "88888 "8%  
  -^  '888"  X888  8888>     .-` X*"    8888            `"*88      X  88888 '  `8888>     
   dx '88~x. !88~  8888>       .xhx.    8888       .xHHhx.."      !  `8888> %  X88!     
 .8888Xf.888x:!    X888X.:   .H88888h.~`8888.>    X88888888hx. ..!    `888X  `~""`   :   
:""888":~"888"     `888*"   .~  `%88!` '888*~    !   "*888888888"        "88k.      .~   
   "~'   "~         ""            `"     ""            ^"***"`            `""*==~~`     
  
</pre>
<pre>
     ...     ..                                 
  =*8888x <"?88h.       .xnnx.  .xx.    
 X>  '8888H> '8888    .f``"888X< `888.  
'88h. `8888   8888    8L   8888X  8888  
'8888 '8888    "88>  X88h. `8888  X888k 
 `888 '8888.xH888x.  '8888 '8888  X8888 
   X" :88*~  `*8888>  `*88>'8888  X8888 
 ~"   !"`      "888>    `! X888~  X8888 
  .H8888h.       ?88    -`  X*"    X8888 
 :"^"88888h.    '!      xH88hx  . X8888 
 ^    "88888hx.+"     .*"*88888~  X888X 
        ^"**""        `    "8%    X888> 
                         .x..     888f  
                        88888    :88f   
                        "88*"  .x8*~    

</pre>
<pre>
        ....        .        ..                    ...     ..                  
   .x88" `^x~  xH(`     :**888H: `: .xH""    =*8888x <"?88h.         oe    
  X888   x8 ` 8888h    X   `8888k XX888      X>  '8888H> '8888        .@88    
 88888  888.  %8888   '8hx  48888 ?8888    '88h. `8888   8888   ==*88888    
<8888X X8888   X8?    '8888 '8888 `8888    '8888 '8888    "88>     88888    
X8888> 488888>"8888x   %888>'8888  8888     `888 '8888.xH888x.     88888    
X8888>  888888 '8888L    "8 '888"  8888       X" :88*~  `*8888>    88888    
?8888X   ?8888>'8888X   .-` X*"    8888     ~"   !"`      "888>    88888    
 8888X h  8888 '8888~     .xhx.    8888      .H8888h.       ?88     88888    
  ?888  -:8*"  <888"    .H88888h.~`8888.>   :"^"88888h.    '!      88888    
   `*88.      :88%     .~  `%88!` '888*~    ^    "88888hx.+"       88888    
      ^"~====""`             `"     ""            ^"**""        '**%%%%%%** </pre>
</div>
