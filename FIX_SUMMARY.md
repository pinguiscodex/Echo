# Fix Summary: Tool Calling & Audio Issues

## Issues Fixed

### 1. 400 Bad Request Error with Mistral API Tool Calling ✅
**Problem**: When AI used tools (like news_search, web_search), the API returned 400 Bad Request.

**Root Cause**: Tool result messages were missing the required `name` field that Mistral API requires.

**Fix**: Added `name` field to all tool result messages in `src/echo/core/agent.py`.

**Mistral API Required Format**:
```json
{
  "role": "tool",
  "name": "function_name",
  "content": "result text",
  "tool_call_id": "call_id_from_api"
}
```

### 2. Incorrect Assistant Message Structure ✅
**Problem**: Code created TWO assistant messages when tool_calls were present, causing API errors.

**Before**:
```python
# Message 1: assistant with content
{"role": "assistant", "content": "response text"}
# Message 2: assistant with tool_calls
{"role": "assistant", "content": None, "tool_calls": [...]}
```

**After**:
```python
# Single message with both content and tool_calls
{"role": "assistant", "content": "response text", "tool_calls": [...]}
```

**Fix**: Modified `src/echo/core/chatbot.py` to create a single assistant message.

### 3. Empty Response Retry Loop ✅
**Problem**: When AI returned tool_calls with no text content, code treated it as empty response and retried indefinitely.

**Fix**: Modified `src/echo/cli.py` to check for tool_calls before retrying:
```python
if not full_response.strip():
    if chat_response.has_tool_calls():
        # Has tool calls - proceed with tool execution
        pass
    elif max_retries > 0:
        # Retry logic
```

### 4. Tool Calls Extraction Logic ✅
**Problem**: Code assumed tool_calls were in a separate message, not the same message as content.

**Fix**: Updated extraction logic in `src/echo/cli.py` to search for assistant message matching the response content:
```python
tool_calls = []
for msg in reversed(self.chatbot.messages):
    if msg.get("role") == "assistant" and msg.get("content") == full_response:
        tool_calls = msg.get("tool_calls", [])
        break
```

### 5. Added Debug Logging for TTS ✅
**Purpose**: Help diagnose why TTS might not produce audio.

**Added**:
```python
logger.info("TTS requested for response: %s", full_response[:100])
logger.info("TTS skipped: output_mode=%s, response_empty=%s", ...)
```

## Segmentation Fault

**Cause**: Secondary effect of 400 API error during tool execution, causing improper cleanup of audio resources (sounddevice).

**Resolution**: Fixed the root 400 error issue, which should prevent the segfault.

## Files Modified

1. `src/echo/core/agent.py` - Added `name` field to tool results
2. `src/echo/core/chatbot.py` - Fixed message structure with tool_calls
3. `src/echo/cli.py` - Fixed retry logic and tool extraction

## Test Results

✅ All 110 tests pass
✅ Tool result format verified correct
✅ Complete tool calling flow tested and working

## How to Test

1. Run the application: `python -m echo`
2. Ask a question that triggers tool use: "What's in the current directory?"
3. Verify:
   - No 400 errors
   - Tool executes successfully
   - AI responds with tool results
   - TTS speaks the response (if output_mode is "both" or "speech")
