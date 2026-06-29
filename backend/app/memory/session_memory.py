conversation_memory = {}


def get_session(session_id: str):
    if session_id not in conversation_memory:
        conversation_memory[session_id] = {
            "intent": None,
            "date": None,
            "time": None,
            "customer_name": None,
            "phone_number": None,
        }

    return conversation_memory[session_id]


def update_session(session_id: str, data: dict):
    session = get_session(session_id)

    for key, value in data.items():
        if value:
            session[key] = value

    return session


def clear_session(session_id: str):
    if session_id in conversation_memory:
        del conversation_memory[session_id]