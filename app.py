import os
import json

from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from groq import Groq


# ==========================================
# SETUP
# ==========================================

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("GROQ_API_KEY not found in .env")

client = Groq(api_key=api_key)

app = Flask(__name__)

MODEL = "openai/gpt-oss-120b"

TODO_FILE = "todos.json"


# ==========================================
# LOAD TODOS
# ==========================================

def load_todos():

    if not os.path.exists(TODO_FILE):
        return []

    try:

        with open(
            TODO_FILE,
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

    with open(
        TODO_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            todos,
            file,
            indent=4
        )


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


    # Prevent duplicates

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

1. Add tasks
2. List tasks
3. Remove tasks
4. Complete tasks

Always use a tool when the user wants to
modify or view their todo list.

If the user asks for multiple actions,
perform them in the correct order.

Example:

"Delete learn Python and then show all tasks"

means:

1. Remove learn Python
2. List the remaining tasks

Another example:

"Complete learn Python and show my tasks"

means:

1. Mark learn Python as completed
2. List the tasks

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

    return send_from_directory(
        ".",
        "index.html"
    )


# ==========================================
# CHAT API
# ==========================================

@app.route(
    "/chat",
    methods=["POST"]
)
def chat():

    try:

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


        # ==============================
        # INITIAL MESSAGE
        # ==============================

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


        # ==============================
        # FIRST AI CALL
        # ==============================

        response = client.chat.completions.create(

            model=MODEL,

            messages=messages,

            tools=tools,

            tool_choice="auto"

        )


        assistant_message = (
            response.choices[0].message
        )


        # ==============================
        # TOOL LOOP
        # ==============================

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


                # Execute function

                result = execute_tool(

                    function_name,

                    arguments

                )


                print(
                    f"Result: {result}"
                )


                # Return result to AI

                messages.append({

                    "role": "tool",

                    "tool_call_id":
                        tool_call.id,

                    "content":
                        json.dumps(result)

                })


            # ==============================
            # AI AGAIN
            # ==============================

            response = client.chat.completions.create(

                model=MODEL,

                messages=messages,

                tools=tools,

                tool_choice="auto"

            )


            assistant_message = (
                response.choices[0].message
            )


        # ==============================
        # FINAL RESPONSE
        # ==============================

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
