"""ask_user tool - Send a question to the user and stop execution.

The question is saved as a visible message in chat (rendered as a yellow question bubble).
The user responds with a normal message, which starts a new agent job.
"""

from typing import Any, Dict, List, Optional

from user_container.tools.registry import ToolSchema, make_parameters
from user_container.agent.context import get_conversation_id
from user_container.logger import log


ASK_USER_SCHEMA = ToolSchema(
    name="ask_user",
    description="""Ask the user a question. The question appears in chat as a special message with clickable options.

Execution STOPS after asking — the user responds in their own time, and you continue in the next turn.

Use when you need:
- Clarification about requirements
- User preference or choice between approaches
- Confirmation before destructive/irreversible actions
- Missing information that only user can provide

Example uses:
- "Which format do you prefer?" with options=["PDF", "DOCX", "Both"]
- "Should I proceed with deleting these files?" with options=["Yes", "No"]
- "What email address should I use?" (no options - free-form input)""",
    parameters=make_parameters({
        "question": {
            "type": "string",
            "description": "The question to ask the user. Be clear and specific.",
        },
        "options": {
            "type": ["array", "null"],
            "items": {"type": "string"},
            "description": "Optional list of choices to present as clickable buttons (e.g., ['PDF', 'DOCX', 'Both']). If not provided, user can type free-form answer.",
        },
    }, required=["question"]),
)


def make_ask_user_tool(job_id: str, job_queue, db=None):
    """
    Create the ask_user tool handler bound to a specific job.

    Args:
        job_id: The job ID to associate with questions
        job_queue: JobQueue instance (used for headless mode only)
        db: Database instance for saving messages to conversation history

    Returns:
        Tool handler function
    """

    def ask_user(args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a question to the user as a visible message.

        Flow:
        1. Save question as assistant message with metadata type="question"
        2. Return signal to stop execution
        3. User sees question in chat, responds with normal message
        4. Agent continues in next job with user's answer in history

        Headless mode: auto-respond with ask_user_default without stopping.
        """
        question = args.get("question")
        if not question:
            raise ValueError("question is required")

        options: Optional[List[str]] = args.get("options")

        log(f"[ask_user] Asking user: {question}")
        if options:
            log(f"[ask_user] Options: {options}")

        # Get conversation_id from context
        conversation_id = get_conversation_id()

        # Check headless mode (scheduled jobs, etc.)
        job_data = job_queue.get_job(job_id)
        is_headless = job_data.get("headless", False) if job_data else False

        if is_headless:
            default_response = (job_data or {}).get("ask_user_default", "proceed")
            log(f"[ask_user] Headless mode - auto-responding: {default_response}")

            # Save question and auto-response to history
            if db and conversation_id:
                question_msg = {"role": "assistant", "content": question}
                metadata = {"type": "question", "options": options}
                db.save_message_from_dict(conversation_id, question_msg, metadata=metadata)

                response_msg = {"role": "user", "content": default_response}
                metadata = {"type": "question_response", "auto": True}
                db.save_message_from_dict(conversation_id, response_msg, metadata=metadata)

            return {
                "status": "success",
                "question": question,
                "response": default_response,
                "auto": True,
            }

        # Save question as visible assistant message (rendered as yellow question bubble)
        if db and conversation_id:
            question_msg = {
                "role": "assistant",
                "content": question
            }
            metadata = {
                "type": "question",
                "options": options
            }
            db.save_message_from_dict(conversation_id, question_msg, metadata=metadata)
            log(f"[ask_user] Saved question message to conversation {conversation_id}")

        # Return immediately - agent loop will detect stop_execution and end the job
        return {
            "status": "sent",
            "stop_execution": True,
            "question": question,
            "message": "Question sent to user. Execution will stop now — user will respond in their next message."
        }

    return ask_user
