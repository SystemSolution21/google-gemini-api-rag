# MULTI-USER RAG Chatbot Architecture

This document outlines the architecture of the multi-user RAG (Retrieval-Augmented Generation) chatbot application.

## User Registration Flow

The application uses a conversational, state-machine-like approach for new user registration. The flow is triggered from the login screen by using a special keyword.

The process is managed within `app_multiuser.py` primarily by two functions: `_handle_registration` and `_handle_registration_step`.

1. **Initiation (from Login Form)**:
    * A user clicks the login button on the Chainlit UI, which opens a custom login form.
    * To start registration, the user enters their desired **email address** and types the keyword **`register`** into the **password field**.
    * The custom authentication backend detects the `register` keyword and sets a `registration_pending: True` flag in the user's session metadata, initiating the registration sequence instead of attempting to log in.
    * The `@cl.on_chat_start` handler detects this flag and calls `_handle_registration` to begin the process.

2. **State Management**:
    * The registration process is a multi-step conversation. The current step is tracked in the `chainlit` user session using the `registration_step` key (e.g., `"username"`, `"email"`, `"password"`).
    * The `@cl.on_message` handler checks for `registration_step` on every incoming message. If it's set, the message content is passed to `_handle_registration_step` instead of being processed as a regular chat message.

3. **Conversational Steps (`_handle_registration_step`)**:
    This function acts as a state machine, guiding the user through the required inputs.

    * **Step 1: Username**: The user is prompted to enter a username.
    * **Step 2: Email**: The user is asked to confirm their email. The email from the OAuth provider is suggested as a default.
    * **Step 3: Password**: The user is prompted to create a password with a minimum length requirement.
    * **Step 4: Password Confirmation**: The user must re-enter the password to confirm it. If it doesn't match, the flow resets to the password step.

4. **Finalization**:
    * Once all steps are successfully completed, the collected information (username, email, password) is retrieved from the user session.
    * The `auth.register_user` function is called to create a new user record in the PostgreSQL database.
    * All registration-related keys are cleared from the user session to exit the registration mode.
    * A success message is displayed, instructing the user to log out and log back in with their new credentials to start a regular chat session.

This design keeps the registration logic contained and leverages the conversational UI of the chatbot, providing a guided and interactive onboarding experience.
