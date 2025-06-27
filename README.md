
previous goal:
- come up with a custom language that the llm can use to compose functions
- it describes what the functions are



I tried to make a "UI Buttons", it turned into dungeons and dragons.


- i keep track of 2 message lists
    - DM messages
    - player messages
- before running, the DM generates a premise for the story
- each iteration:   
    - user enters a choice
    - the DM generates new story
    - the player generates 3 new choices
- the external input is the choice
- the game loop is:
    - generate story
    - generate choices
    - get user input for choice
- in this case, my solution is not good
    - there should be a guarantee that story generation is blocked on choice
    - and the story should proceed linearly



Step 2: kubernetes and dragons
- make the same thing as choices2.py, but have it call kubectl commands
- 3 or 4 options are provided, each option is a bash command
    - each option gets ran as a bash command in a container with read only access to the kubernetes cluster
    - if an option returns a failed exit code, the LLM retries
- the player chooses one of the 3-to-4 options, it gets added to the 'research queue'
- the player can click an 'act' button, switching to a new mode
    - the new mode has a read-write kubernetes service account, and the commands are not run automatically
    - 3-to-4 commands are still generated, the player authorized one of the commands to be run
- maybe the LLM should be given a choice of previously ran commands to validate the fix is effective
    - the first step in debugging an issue is identifying the issue
    - generating a command to identify an issue is a task
    - after running a command to fix the issue, we want to verify it has been fixed
    - 



more general ui builder:
- the llm generates a collection of potential actions the user can take
    - each action has text for it
- the llm generates UI elements for each potential action
- the llm chooses an arrangement for the UI elements
- the UI elements are rendered as buttons
- when a user presses a button, the text for the action for that button gets added to the context
- the llm has a loop that runs the rest of the simulation
- at some point, the simulation decides to take an action
- the simulation generates a collection of potential actions
- the results of the previous action gets 


the buttons are like predictive text?

"seek reflection's heart"
"echoes of self, reflections reveal the thresholds"
"Midnight sentinel awaits."




An interseting idea from Jeremy:
1. the DM model
2. the Player model
3. a third Scribe model
- the DM model creates the premise of the story
- the Player creates a character sheet
- the Player creates 3 choices for the user to choose from
- the use chooses, then the DM creatively imagines the effects of that action
- over time, the Scribe interprets the previous n-messages and enters them into a historical record
- when the DM generates descriptions, it uses a combination of the previous n-messages and the historical record



export KUBECONFIG=./readonly-kubeconfig



something we could reasonably do:
1. ask the LLM to make a list of "check state" bash commands, parametric
2. have the LLM generate some tests for the commands
3. provide the commands as options for the LLM when getting actions
4. have the LLM generate function calls from that list
5. render the function calls as buttons with their parameters
    colorize them by group
    if the function is read-only, run it and show results
6. when a button is pressed, add the record to the debug information



maybe we shouldn't retain a whole message history
maybe we should just retain the Insights list?
if it can compress its own ideas



ToDo Next:
- make buttons selectable, send all at the same time, record multiple commands



Probably the right thing to do is have a "Summary" struct.
Have the LLM generate the "Summary" regularly.
And only retain one instance of the "Summary" in the message history. 




A good way to extract value from an LLM is to have it produce structured output and iterate on the structured output.
The LLM will think and it will try things and it will coalesce the text it receives and the text it generates into 
the structured output, iteratively updating it through several steps. 
The structured output can be described in a way that reflects the information we want to extract, but instead of 
asking it to extract the information in one-shot, we can ask it to refine the structure.
Is there a way we could write a class that managing a struct? 
Obviously the struct would be extractable with a get_struct() function or something, but given that it updates the 
struct, it could also emit events when the struct has been changed. 



1. prepare the LLM with a long message history, primarily as a way to describe context before generation, not so much more giving the LLM logic to follow.
2. create a typed struct that represents the state of the task I'm trying to solve
3. have the LLM generate the struct using with_structured_output, retry until it works
4. when the LLM generates the state struct, it gets added the end of the message list, but the struct only exists once in the list. when a new state struct is added, all previous versions get removed.
5. when other things in the system change, the message list for this LLM gets updated and the status struct gets changed.
6. wrap all of this in a class. emit an event when struct data changes.







maybe the Structuralizer instances should "register" for message updates of other streams
and the Structuralizer would get set up with Filters, instead of choosing individual messages to send
sometimes it makes sense to divert the messages though



