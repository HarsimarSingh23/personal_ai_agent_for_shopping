import json
import logging
import re
from typing import List, Dict
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from llm import _ask

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a highly capable and empathetic personal AI shopping assistant.
Your goal is to help the user find the perfect item by asking them conversational questions.
Be concise, engaging, and use a friendly tone.

RULES:
1. Keep track of what information has been provided.
2. If the user's request is too vague, ask 1 or 2 follow-up questions to gather key preferences (like brand or specific features). Do NOT ask for a budget unless strictly necessary.
3. If the user provides enough details (e.g., "i7 gaming laptop"), you can search immediately without asking more questions.
4. If the user confirms a summary with "yes", or if you have enough information, you MUST set "is_ready_to_search" to true.
5. Your response MUST be a valid JSON object with the following keys:
   - "message": Your reply. IMPORTANT: If "is_ready_to_search" is true, this message MUST NOT be a question. It must be a short acknowledgment like "Got it! Let me find the best options for you."
   - "is_ready_to_search": boolean. True if you have enough info to search, False otherwise.
   - "search_query": string containing a concise search query (3-6 words) for Amazon/Flipkart. ONLY populate this if is_ready_to_search is True.

CONVERSATION HISTORY:
"""

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
def _get_chat_response(prompt: str) -> Dict:
    raw_response = _ask(prompt)
    try:
        clean = re.sub(r"^```(?:json)?\s*", "", raw_response.strip(), flags=re.MULTILINE)
        clean = re.sub(r"\s*```$", "", clean).strip()
        result = json.loads(clean)
        return {
            "message": result.get("message", "I'm looking that up for you!"),
            "is_ready_to_search": bool(result.get("is_ready_to_search", False)),
            "search_query": result.get("search_query", "")
        }
    except Exception as e:
        log.warning(f"JSON parsing failed, triggering retry... Error: {e} Raw: {raw_response}")
        raise ValueError(f"Failed to parse JSON: {e}")

def process_chat(history: List[Dict[str, str]]) -> Dict:
    """
    Takes a list of conversation messages [{"role": "user"/"agent", "content": "..."}]
    and returns a JSON dict with the agent's response, search status, and query.
    """
    prompt = SYSTEM_PROMPT.strip() + "\n"
    for msg in history:
        role = msg.get("role", "user").upper()
        content = msg.get("content", "")
        prompt += f"\n{role}: {content}"
    prompt += "\n\nOutput only the valid JSON response:"
    
    try:
        response = _get_chat_response(prompt)
        
        # --- Production Anti-Loop Guardrails ---
        if not response["is_ready_to_search"] and len(history) >= 2:
            last_user_msg = history[-1].get("content", "").strip().lower()
            last_agent_msg = history[-2].get("content", "").strip()
            
            # Guardrail 1: If user just confirmed, forcefully break out and search
            if last_user_msg in ["yes", "yep", "yeah", "correct", "exactly"]:
                log.info("Guardrail triggered: user confirmed, forcing search.")
                response["is_ready_to_search"] = True
                response["message"] = "Got it! Finding the best options for you now..."
                
                # Try to extract a query from the agent's last confirmation question
                clean_query = last_agent_msg.replace("So, you're looking for", "").replace("an ", "").replace("a ", "").replace("?", "").strip()
                response["search_query"] = clean_query if clean_query else "laptop"
            
            # Guardrail 2: If LLM is repeating itself verbatim, force search to break loop
            elif response["message"].strip() == last_agent_msg:
                log.info("Guardrail triggered: LLM repeated itself, forcing search.")
                response["is_ready_to_search"] = True
                response["message"] = "Let me look that up for you right now."
                response["search_query"] = last_user_msg
                
        return response
    except Exception as e:
        log.error(f"All retries failed for chat_agent: {e}")
        # Fallback if the LLM completely fails 3 times
        return {
            "message": "I think I have enough to go on! Let's see what we can find.",
            "is_ready_to_search": True,
            "search_query": history[-1].get("content", "fashion") if history else "fashion"
        }
