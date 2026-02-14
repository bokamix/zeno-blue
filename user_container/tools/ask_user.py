"""ask_user tool - Pause execution and ask user for input."""

import json
import time
from typing import Any, Dict, List, Optional

from user_container.tools.registry import ToolSchema, make_parameters
from user_container.agent.context import get_conversation_id
from user_container.logger import log


ASK_USER_SCHEMA = ToolSchema(
    name="ask_user",
    description="""Ask the user a question and wait for their response.

Use when you need:
- Clarification about requirements
- User preference or choice
- Confirmation before proceeding
- Missing information that only user can provide

Execution PAUSES until user responds (timeout: 5 minutes).

Example uses:
- "Which format do you prefer: PDF or DOCX?"
- "Should I proceed with deleting these files?"
- "What email address should I use?"
""",
    parameters=make_parameters({
        "question": {
            "type": "string",
            "description": "The question to ask the user. Be clear and specific.",
        },
        "options": {
            "type": ["array", "null"],
            "items": {"type": "string"},
            "description": "Optional list of choices to present (e.g., ['PDF', 'DOCX', 'Both']). If not provided, user can type free-form answer.",
        },
    }),
)


# Timeout for user response (5 minutes)
ASK_USER_TIMEOUT_SECONDS = 300


def make_ask_user_tool(job_id: str, job_queue, db=None):
    """
    Create the ask_user tool handler bound to a specific job.

    Args:
        job_id: The job ID to associate with questions
        job_queue: JobQueue instance for storing questions and waiting for responses
        db: Database instance for saving messages to conversation history

    Returns:
        Tool handler function
    """

    def ask_user(args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ask user a question and wait for response.

        Flow:
        1. Save question as assistant message with metadata type="question"
        2. Store question in job queue, set job status to 'waiting_for_input'
        3. Wait for user_response (blocking via threading.Event)
        4. Save user response as user message
        5. Return response to agent
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

        # 1. Save question as assistant message (visible in chat history)
        if db and conversation_id:
            question_msg = {
                "role": "assistant",
                "content": question
            }
            # Metadata marks this as a question for special rendering in frontend
            metadata = {
                "type": "question",
                "options": options
            }
            db.save_message_from_dict(conversation_id, question_msg, metadata=metadata)
            log(f"[ask_user] Saved question message to conversation {conversation_id}")

        # 2. Store question and set status to waiting_for_input
        job_queue.set_question(job_id, question, options)

        # 3. Wait for user response (blocking - runs in worker thread)
        response = job_queue.wait_for_response_sync(job_id, timeout=ASK_USER_TIMEOUT_SECONDS)

        if response:
            log(f"[ask_user] Got response: {response}")

            # 4. Save user response as user message (visible in chat history)
            if db and conversation_id:
                response_msg = {
                    "role": "user",
                    "content": response
                }
                # Metadata marks this as answer to question
                metadata = {"type": "question_response"}
                db.save_message_from_dict(conversation_id, response_msg, metadata=metadata)
                log(f"[ask_user] Saved response message to conversation {conversation_id}")

            return {
                "status": "success",
                "question": question,
                "response": response
            }

        # 5. Timeout - no response
        log(f"[ask_user] Timeout after {ASK_USER_TIMEOUT_SECONDS}s")
        return {
            "status": "timeout",
            "question": question,
            "error": f"User did not respond within {ASK_USER_TIMEOUT_SECONDS // 60} minutes"
        }

    return ask_user
