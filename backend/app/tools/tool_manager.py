class ToolManager:
    def execute(self, tool_name: str, payload: dict):
        return {
            "tool": tool_name,
            "payload": payload,
        }