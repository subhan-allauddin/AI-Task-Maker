import os
import json

from flask import Flask, request, jsonify, send_file
from dotenv import load_dotenv
from groq import Groq


# ==========================================
# SETUP
# ==========================================

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

client = Groq(api_key=api_key) if api_key else None

app = Flask(__name__)

MODEL = "openai/gpt-oss-120b"

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

IS_SERVERLESS = os.environ.get("VERCEL") == "1"


def todo_file():

    if IS_SERVERLESS:

        return os.path.join("/tmp", "todos.json")

    return os.path.join(BASE_DIR, "todos.json")


def index_file():

    return os.path.join(BASE_DIR, "index.html")


# ==========================================
# LOAD TODOS
# ==========================================

def load_todos():

    path = todo_file()

    if not os.path.exists(path):
        return []

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except:

        return []


todos = load_todos()


# ==========================================
# SAVE TODOS
# ==========================================

def save_todos():

    try:

        with open(
            todo_file(),
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                todos,
                file,
                indent=4
            )

    except OSError:

        pass


# ==========================================
# ADD TODO
# ==========================================

def add_todo(task):

    task = task.strip()

    if not task:

        return {
            "success": False,
            "message": "Task cannot be empty.",
            "todos": todos
        }


    for todo in todos:

        if todo["task"].lower() == task.lower():

            return {
                "success": False,
                "message": "That task already exists.",
                "todos": todos
            }


    todos.append({

        "task": task,

        "completed": False

    })


    save_todos()


    return {

        "success": True,

        "message":
            f"Added '{task}' to your todo list.",

        "todos": todos

    }


# ==========================================
# ADD MULTIPLE TODOS
# ==========================================

def add_multiple_todos(tasks):

    if not tasks:

        return {
            "success": False,
            "message": "No tasks provided.",
            "todos": todos
        }


    added = []
    skipped = []


    for task in tasks:

        task = task.strip()

        if not task:
            continue


        exists = False

        for todo in todos:

            if todo["task"].lower() == task.lower():

                exists = True
                break


        if exists:

            skipped.append(task)

        else:

            todos.append({

                "task": task,

                "completed": False

            })

            added.append(task)


    save_todos()


    message_parts = []

    if added:

        message_parts.append(
            f"Added {len(added)} task(s): "
            + ", ".join(f"'{t}'" for t in added)
        )

    if skipped:

        message_parts.append(
            f"Skipped {len(skipped)} duplicate(s): "
            + ", ".join(f"'{t}'" for t in skipped)
        )


    if not message_parts:

        message_parts.append("No tasks were added.")


    return {

        "success": True,

        "message": " ".join(message_parts),

        "todos": todos

    }


# ==========================================
# LIST TODOS
# ==========================================

def list_todos():

    return {

        "success": True,

        "todos": todos

    }


# ==========================================
# REMOVE TODO
# ==========================================

def remove_todo(task):

    task = task.strip()


    for todo in todos:

        if todo["task"].lower() == task.lower():

            todos.remove(todo)

            save_todos()


            return {

                "success": True,

                "message":
                    f"Removed '{todo['task']}'.",

                "todos": todos

            }


    return {

        "success": False,

        "message":
            f"Could not find '{task}'.",

        "todos": todos

    }


# ==========================================
# COMPLETE TODO
# ==========================================

def complete_todo(task):

    task = task.strip()


    for todo in todos:

        if todo["task"].lower() == task.lower():

            todo["completed"] = True

            save_todos()


            return {

                "success": True,

                "message":
                    f"Completed '{todo['task']}'.",

                "todos": todos

            }


    return {

        "success": False,

        "message":
            f"Could not find '{task}'.",

        "todos": todos

    }


# ==========================================
# TOOL DEFINITIONS
# ==========================================

tools = [

    {

        "type": "function",

        "function": {

            "name": "add_todo",

            "description":
                "Add a new task to the todo list.",

            "parameters": {

                "type": "object",

                "properties": {

                    "task": {

                        "type": "string",

                        "description":
                            "The task to add."

                    }

                },

                "required": ["task"]

            }

        }

    },


    {

        "type": "function",

        "function": {

            "name": "add_multiple_todos",

            "description":
                "Add multiple tasks to the todo list at once. "
                "Use this when the user provides several tasks "
                "in one message, separated by commas, 'and', "
                "newlines, or any other delimiter.",

            "parameters": {

                "type": "object",

                "properties": {

                    "tasks": {

                        "type": "array",

                        "items": {

                            "type": "string"

                        },

                        "description":
                            "A list of tasks to add."

                    }

                },

                "required": ["tasks"]

            }

        }

    },


    {

        "type": "function",

        "function": {

            "name": "list_todos",

            "description":
                "Show all tasks in the todo list.",

            "parameters": {

                "type": "object",

                "properties": {}

            }

        }

    },


    {

        "type": "function",

        "function": {

            "name": "remove_todo",

            "description":
                "Remove a task from the todo list.",

            "parameters": {

                "type": "object",

                "properties": {

                    "task": {

                        "type": "string",

                        "description":
                            "The task to remove."

                    }

                },

                "required": ["task"]

            }

        }

    },


    {

        "type": "function",

        "function": {

            "name": "complete_todo",

            "description":
                "Mark a todo task as completed.",

            "parameters": {

                "type": "object",

                "properties": {

                    "task": {

                        "type": "string",

                        "description":
                            "The task to mark as completed."

                    }

                },

                "required": ["task"]

            }

        }

    }

]


# ==========================================
# SYSTEM PROMPT
# ==========================================

SYSTEM_MESSAGE = """

You are a helpful AI To-Do Assistant.

You can:

1. Add tasks (single or multiple at once)
2. List tasks
3. Remove tasks
4. Complete tasks

Always use a tool when the user wants to
modify or view their todo list.

If the user provides multiple tasks in one
message (e.g., "add buy milk, walk the dog,
and finish homework"), use the
`add_multiple_todos` tool to add them all
at once.

If the user asks for multiple actions,
perform them in the correct order.

Examples:

"Delete learn Python and then show all tasks"

means:

1. Remove learn Python
2. List the remaining tasks

"Complete learn Python and show my tasks"

means:

1. Mark learn Python as completed
2. List the tasks

"Add buy groceries, call mom, and clean room"

means:

1. Use add_multiple_todos with
   ["buy groceries", "call mom", "clean room"]

Note: User input may come from voice
transcription, so it may contain small
typos or filler words. Interpret the
intent, not the exact wording.

Be concise and friendly.

"""


# ==========================================
# EXECUTE TOOL
# ==========================================

def execute_tool(
    function_name,
    arguments
):

    if function_name == "add_todo":

        return add_todo(
            arguments.get("task", "")
        )


    if function_name == "add_multiple_todos":

        return add_multiple_todos(
            arguments.get("tasks", [])
        )


    if function_name == "list_todos":

        return list_todos()


    if function_name == "remove_todo":

        return remove_todo(
            arguments.get("task", "")
        )


    if function_name == "complete_todo":

        return complete_todo(
            arguments.get("task", "")
        )


    return {

        "success": False,

        "message":
            "Unknown tool."

    }


# ==========================================
# HOME PAGE
# ==========================================

@app.route("/")
def home():

    return send_file(index_file())


# ==========================================
# CHAT API
# ==========================================

@app.route(
    "/chat",
    methods=["POST"]
)
def chat():

    try:

        if client is None:

            return jsonify({
                "error":
                    "GROQ_API_KEY is not set."
            }), 500


        data = request.get_json()


        if not data:

            return jsonify({

                "error":
                    "Invalid request."

            }), 400


        user_message = data.get(
            "message",
            ""
        ).strip()


        if not user_message:

            return jsonify({

                "error":
                    "Message is empty."

            }), 400


        messages = [

            {

                "role": "system",

                "content":
                    SYSTEM_MESSAGE

            },

            {

                "role": "user",

                "content":
                    user_message

            }

        ]


        response = client.chat.completions.create(

            model=MODEL,

            messages=messages,

            tools=tools,

            tool_choice="auto"

        )


        assistant_message = (
            response.choices[0].message
        )


        while assistant_message.tool_calls:

            messages.append(
                assistant_message
            )


            for tool_call in (
                assistant_message.tool_calls
            ):

                function_name = (
                    tool_call.function.name
                )


                arguments = json.loads(

                    tool_call.function.arguments

                )


                print(
                    f"\nTool: {function_name}"
                )

                print(
                    f"Arguments: {arguments}"
                )


                result = execute_tool(

                    function_name,

                    arguments

                )


                print(
                    f"Result: {result}"
                )


                messages.append({

                    "role": "tool",

                    "tool_call_id":
                        tool_call.id,

                    "content":
                        json.dumps(result)

                })


            response = client.chat.completions.create(

                model=MODEL,

                messages=messages,

                tools=tools,

                tool_choice="auto"

            )


            assistant_message = (
                response.choices[0].message
            )


        final_text = (
            assistant_message.content
        )


        if not final_text:

            final_text = "Done."


        return jsonify({

            "reply": final_text,

            "todos": todos

        })


    except Exception as e:

        print("\nERROR:")

        print(e)


        return jsonify({

            "error":
                str(e)

        }), 500


# ==========================================
# START SERVER
# ==========================================

if __name__ == "__main__":

    app.run(debug=True)