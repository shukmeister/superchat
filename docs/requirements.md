# superchat Requirements

## Goal
To facilitate AI-driven discussions for research, exploration, discussion, and idea refinement.

## Background
superchat is a terminal-based command-line interface (CLI) application for communicating with AIs. The goal is to enable standardized and customizable access to AIs for information retrieval, conversational discourse, and multi-agent group debates. Besides for 1:1 conversations with individual AIs, the system allows a user to ask a question, receive independent answers from multiple AIs, engage in private back-and-forth conversations to refine answers, and then initiate a group debate where AIs discuss their answers, guided by the user as a human intermediary. In order to stay flexible to a large variety of tasks, the system can be customized with many selections of models, voice output, internet access, multi-agent output, and more.

## Technical Specifications
- Python 3.8+
- Autogen via python (pyautogen library)
- Openrouter will provide the AIs
- Try to avoid using any CLI TUI library but if absolutely necessary use blessed
- Each agent should have a background prompt that specifies that it is in a discourse with other AIs and that it should review each other AIs inputs and then make its own recommendations. If it disagrees with another AI, it should specify why. The background prompt guides disagreement rationale.

### Installation & Distribution
- **Package Structure**: Create `pyproject.toml` with console script entry point
- **Installation Method**: Users install directly from private repository using `pip install git+https://github.com/username/superchat.git`
- **Command Access**: After installation, users can run `superchat` from any terminal location
- **Dependencies**: All Python dependencies automatically handled during pip installation
- **Updates**: Users can update with `pip install --upgrade git+https://github.com/username/superchat.git`

## User Interface
superchat is accessed through a unix system terminal CLI interface. After starting the system in the terminal with the below startup command, a TUI chat interface will open.

When the program is started, it will be in a setup mode where the user can define the parameters of the chat they want to have. On the top of the terminal output, the program will display (1) an ASCI art of the name “superchat”, and (2) some information about the current session, such as models selected, and other optional parameters which have been selected. These parameters can either be selected during startup by passing flags in with the startup command (such as --voice to enable voice output). Underneath this startup info section will be the start of the chat app interface, which will simply be a > icon. The user can then add text to send to the AI here or they can pass commands. Various startup commands are sent to configure the parameters of the chat session until the user is ready to start the chat, at which point they send the /start command and the chat starts.

### Command Syntax
| Command | Syntax | Description |
|---------|--------|-------------|
| Startup | `~ % superchat`<br>`~ % sc` | Starts superchat from the terminal, can be accessed globally on the system |
| List models | `/list` | List out all the models available to interface with. Only available in setup stage |
| Select model | `/model` | Select a model to interface with. Requires a parameter that is a model’s name and also its slot number. If a model is already taken in that slot, then it overwrites the previously specified model in that slot. Only available in setup stage. |
| Remove model | `/remove` | Removes a model from the chat during setup. Requires a parameter that is a model’s name. Only available in setup stage |
| Voice mode | `/voice` | Triggers voice mode, where the models will have their text responses also read out as a voice |
| Promote model | `/promote` | If in a 1:1 chat before a debate, this ends the 1:1 chat session and promotes all that chat context into the main debate chat thread. |
| Boot model | `/boot` | Excludes a specific model from continuing in the chat. If used in a 1:1 chat, it cancels that chat session and moves on to a 1:1 with another model if applicable. If used in a debate with multiple AIs, it kicks out the specified AI from continuing in the conversation. If more than one AI is in the chat when used, this command requires a parameter that is the model’s name to be booted. |
| Restart model | `/restart` | Restart a chat Numericable model when having a 1:1, removes and wipes all context and starts a fresh chat |
| Statistics | `/stats` | Shows information about the current session, including (1) time elapsed, (2) number of conversational rounds (back-and-forths) for each AI and also total, and (3) number of input and output tokens per AI and total for the entire session. This is restarted after each session (meaning each time the program is run) |
| Help | `/help` | Displays a list of all the different commands that can be executed. Note: as a new command is added to the app, it should also be added to the help info output |
| Ask model | `/ask` | Ask a question to a specific AI, requires the name of the AI as the parameter. Only that AI responds to the question. |
| Exit session | `/exit` | Ends the chat session |

If CLI parameters are passed in with the command line “superchat” command then those args are used instead of the setup phase of the chat, for example a “superchat -m k1 -v” command will instantly start a chat with k1 with voice mode on, instead of requiring going through the setup phase. 

CLI parameters will exist for many of the commands, for example:
- `--model k2 --model r1 --model o3`
- `--model, -m`
- `--voice, -v`

These are the same customizations as in the setup mode, so they can be passed in through either startup flags or TUI commands.

### Example
```
~ % superchat

SUPERCHAT
[Information about current session]

>> /model 1 k2
>> /model 2 r1
>> /model 3 o3
>> /voice
>> /start

>> [k2] How can I help?
```

### Chat TUI
The multi-AI chat format has user messages prefixed with > and separated by blank lines, followed by multiple AI responses each tagged with their identifier (like [k2]:, [o3]:, [r1]:). Note that there is a russian letter indicating which AI is speaking. For example:

```
> What's the meaning of life?

д [k2]: That's a philosophical question that's puzzled humanity for centuries...
ф [o3]: Some say it's 42, but I think it's about finding purpose and connection.
ш [r1]: Love, create, learn, repeat. Simple but profound.

> How do I make coffee?

д [k2]: Start with good beans, grind them fresh, use hot water around 200°F...
ф [o3]: Don't forget the ratio - about 1:15 coffee to water by weight.
ш [r1]: And bloom the grounds first! Pour a little water, wait 30 seconds.
```

## Requirements
Here’s a collection of additional requirements for this program. Note this is not an exhaustive list.
- Two of the same AI cannot be selected
- Internet search
  - Automatic search: If an AI cannot answer confidently (based on LLM judgment), it performs a web search and includes results in its response, e.g., [Agent1]: [Based on web search] Python is popular...
  - Explicit Search: User can trigger a search with “search: [query]” (e.g., “to Agent1: search: best programming language”).
- Show a final summary when the user types47 “/exit”, including total tokens and costs.
- If no command is used during a chat, then the user will either input additional text or input no text. If the user put additional text, then that is considered additional context or another question, based on the text that is provided, then all the AIs will respond in a round robin fashion. Each AI will be able to see the responses of the other AIs.
- A list of available models, including API keys and the names, should be stored in the source code somewhere
- During debate initialization, the system shall sequentially append each AI's full 1:1 transcript (except for the original prompt) in setup order (e.g., AI1's entire dialogue → AI2's entire dialogue), preserving internal chronological order without cross-AI message interleaving or restructuring.
- When the debate begins, the original prompt is shared once at the top, then the AIs full 1:1 transcripts with each AI, then the debate chat underneath that
- If the user sends no message, then it will trigger another round robin of conversation between the AIs without any additional user input.
- If more than 1 model is selected during setup, the chat will be a “debate” style conversation where the AIs will all discuss the prompt together. Before the AIs begin discussing and debating with one another, the user can have a 1:1 private conversation with each AI. The flow goes like this:
  - Program starts
  - User inputs the parameters of the AI debate in the setup phase, ex: 3 models
  - User begins the chat with /start
  - User sends the preliminary prompt to all 3 AIs. This prompt is the background and important information about what the debate will be regarding
  - The background prompt should be defined in the source code of the app
  - User then has a 1:1 conversation with the 1st model about this. A status is shown indicating which AI the user is talking to at all times throughout the chats. The user goes back and forth with the 1st model discussing the topic until the user is satisfied at which point the user uses the /promote, /restart/, or /boot commands, which define what happens to this 1:1 chat. Promote moves the contents of the 1:1 chat to the debate chat, which has all the conversations with all the AIs. Restart deletes this conversation and restarts it again with a fresh context with the same AI. Boot deletes the conversation and moves on to the next model without promoting the conversation to the
  - When this happens, the user then has another 1:1 conversation with the next model and this process repeats.
  - Once all the 1:1 chats have been promoted (or terminated), then the debate begins. In the debate, the original prompt is shared once at the top, then all the chats from each 1:1 are pasted into the chat (to show context of the conversations for all the other AIs to see). Note, the original prompt is not repeated again each time for each 1:1 chat pasted. Then after all the context is shared, the Ais can begin discussing and debating with one another.
- Debate agent order in the conversation follows the slot number (ex: model in slot 1 goes first, then model in slot 2, etc)