import logging
import operator
import json
import os
import asyncio
from typing import List, Dict, Any, Optional, Literal, Annotated
from datetime import datetime
from uuid import uuid4

from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    AnyMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.messages.utils import trim_messages, count_tokens_approximately
from langchain_core.tools import tool
from mistralai import Mistral
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langgraph.graph.message import RemoveMessage, REMOVE_ALL_MESSAGES, add_messages
from pydantic import BaseModel, Field
from psycopg import connect
from psycopg.rows import dict_row

from app.deps.runtime_prod import CHECKPOINTER_POSTGRES
from app.core.constants import DEFAULT_USER_ID
from app.db.session import get_db

load_dotenv()

logger = logging.getLogger(__name__)


def get_ai_settings_from_db(user_id: str = DEFAULT_USER_ID) -> dict:
    """Récupérer les paramètres AI depuis la base de données"""
    try:
        db = get_db()
        result = db.table("ai_settings").select("*").eq("user_id", user_id).execute()
        
        if result.data:
            settings = result.data[0]
            return {
                "model_name": settings.get("model_name", "mistral-small-2506"),
                "system_prompt": settings.get("system_prompt", "You are a helpful AI assistant."),
                "temperature": float(settings.get("temperature", 0.7)),
                "max_tokens": int(settings.get("max_tokens", 2000)),
                "top_p": float(settings.get("top_p", 1.0)) if settings.get("top_p") else None,
                "frequency_penalty": float(settings.get("frequency_penalty", 0.0)) if settings.get("frequency_penalty") else None,
                "presence_penalty": float(settings.get("presence_penalty", 0.0)) if settings.get("presence_penalty") else None,
            }
        
        return {
            "model_name": "mistral-small-2506",
            "system_prompt": "You are a helpful AI assistant specialized in customer support. Be friendly, professional, and concise.",
            "temperature": 0.7,
            "max_tokens": 2000,
            "top_p": None,
            "frequency_penalty": None,
            "presence_penalty": None,
        }
    except Exception as e:
        logger.error(f"Error loading AI settings from DB: {e}")
        return {
            "model_name": "mistral-small-2506",
            "system_prompt": "You are a helpful AI assistant specialized in customer support. Be friendly, professional, and concise.",
            "temperature": 0.7,
            "max_tokens": 2000,
            "top_p": None,
            "frequency_penalty": None,
            "presence_penalty": None,
        }


def _get_or_create_event_loop():
    """Get existing event loop or create a new one"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("Event loop is closed")
        return loop
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


def create_escalation_tool(user_id: str, conversation_id: str):
    """Create escalation tool for routing to human support"""
    from app.services.escalation import Escalation

    escalation_service = Escalation(user_id=user_id, conversation_id=conversation_id)

    @tool
    def escalate_to_human(reason: str, summary: str) -> dict:
        """
        Escalate the conversation to human support when the AI cannot help.

        Use this when:
        - Customer explicitly requests human support
        - Issue is too complex for AI
        - Customer is frustrated or angry
        - Legal, financial, or sensitive matters

        Args:
            reason: Short reason for escalation (e.g., "complex_issue", "customer_request")
            summary: Brief summary of the customer's issue and conversation context

        Returns:
            dict with escalation_id and status
        """
        try:
            loop = _get_or_create_event_loop()
            escalation_id = loop.run_until_complete(
                escalation_service.create_escalation(
                    message=summary,
                    confidence=0.8,
                    reason=reason
                )
            )

            if escalation_id:
                return {
                    "status": "success",
                    "escalation_id": escalation_id,
                    "message": "Conversation escalated to human support. A team member will contact the customer soon."
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to create escalation. Please try again."
                }
        except Exception as e:
            logger.error(f"Escalation tool error: {e}")
            return {"status": "error", "message": str(e)}

    return escalate_to_human


def create_check_availability_tool(user_id: str, conversation_id: str):
    """Create tool to check available appointment slots"""
    from app.services.booking import BookingService

    booking_service = BookingService(user_id=user_id, conversation_id=conversation_id)

    @tool
    def check_availability(start_date: str, end_date: str, timezone: str = "Europe/Paris") -> dict:
        """
        Check available time slots for booking appointments.

        Args:
            start_date: Start date in ISO 8601 format (e.g., "2025-11-20T00:00:00Z")
            end_date: End date in ISO 8601 format (e.g., "2025-11-21T00:00:00Z")
            timezone: Timezone for the slots (default: "Europe/Paris")

        Returns:
            dict with available_slots: list of time slots with start/end times
        """
        try:
            # Check if Cal.com is configured
            cal_api_key = os.getenv("CAL_API_KEY")
            cal_event_type_id = os.getenv("CAL_EVENT_TYPE_ID")

            if not cal_api_key or not cal_event_type_id:
                return {
                    "available_slots": [],
                    "count": 0,
                    "error": "cal_not_configured",
                    "message": "Appointment booking is not configured yet. Please ask the user to connect their Cal.com account first."
                }

            loop = _get_or_create_event_loop()
            slots = loop.run_until_complete(
                booking_service.check_availability(
                    start_date=start_date,
                    end_date=end_date,
                    timezone=timezone
                )
            )

            return {
                "available_slots": [{"start": slot.start, "end": slot.end} for slot in slots],
                "count": len(slots)
            }
        except Exception as e:
            logger.error(f"Check availability error: {e}")
            return {"available_slots": [], "count": 0, "error": str(e)}

    return check_availability


def create_booking_tool(user_id: str, conversation_id: str):
    """Create tool to book appointments"""
    from app.services.booking import BookingService

    booking_service = BookingService(user_id=user_id, conversation_id=conversation_id)

    @tool
    def create_booking(
        attendee_name: str,
        attendee_email: str,
        start_time: str,
        duration_minutes: int = 30,
        attendee_phone: str = None,
        timezone: str = "Europe/Paris"
    ) -> dict:
        """
        Create an appointment booking.

        **CRITICAL**: This tool MUST ONLY be called AFTER:
        1. Calling check_availability to get available slots
        2. Verifying that start_time is in the available_slots list returned by check_availability
        3. Confirming with the customer that they want to book this specific time slot

        **NEVER** call this tool without first verifying availability. If you call this tool with a time that wasn't verified as available, the booking may fail.

        Args:
            attendee_name: Customer's full name
            attendee_email: Customer's email address
            start_time: Booking start time in ISO 8601 UTC format (e.g., "2025-11-20T14:00:00Z"). MUST be from available_slots.
            duration_minutes: Meeting duration in minutes (default: 30)
            attendee_phone: Optional phone number in international format (e.g., "+33612345678")
            timezone: Customer's timezone (default: "Europe/Paris")

        Returns:
            dict with booking details including meeting_url and scheduled_at
        """
        try:
            # Check if Cal.com is configured
            cal_api_key = os.getenv("CAL_API_KEY")
            cal_event_type_id = os.getenv("CAL_EVENT_TYPE_ID")

            if not cal_api_key or not cal_event_type_id:
                return {
                    "status": "error",
                    "message": "Appointment booking is not configured yet. Please ask the user to connect their Cal.com account first."
                }

            loop = _get_or_create_event_loop()
            result = loop.run_until_complete(
                booking_service.create_booking(
                    attendee_name=attendee_name,
                    attendee_email=attendee_email,
                    start_time=start_time,
                    duration_minutes=duration_minutes,
                    attendee_phone=attendee_phone,
                    timezone=timezone
                )
            )

            if result.success:
                return {
                    "status": "success",
                    "booking_id": result.booking_id,
                    "meeting_url": result.meeting_url,
                    "scheduled_at": result.scheduled_at,
                    "message": f"Appointment booked successfully for {attendee_name}"
                }
            else:
                return {
                    "status": "error",
                    "message": result.error_message or "Failed to create booking"
                }
        except Exception as e:
            logger.error(f"Create booking error: {e}")
            return {"status": "error", "message": str(e)}

    return create_booking


def create_search_tool(user_id: str):
    from app.services.rag import rag_service
    from app.services.ingest_helper import get_embedding
    from mistralai import Mistral

    mistral_client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))

    @tool
    def search(search_query: str) -> dict:
        """
        Search the knowledge base for relevant information.

        Args:
            search_query: The text to search for in the knowledge base

        Returns:
            dict with:
            - chunks: List of relevant text chunks (max 3 after reranking)
        """
        try:
            qdrant = rag_service._get_client()
            
            loop = _get_or_create_event_loop()
            embedding = loop.run_until_complete(get_embedding(search_query))
            
            results = qdrant.search(
                collection_name="knowledge_base",
                query_vector=embedding,
                limit=10,
                query_filter={
                    "must": [
                        {"key": "user_id", "match": {"value": user_id}}
                    ]
                }
            )

            chunks = [
                {
                    "content": hit.payload.get("content", ""),
                    "score": hit.score,
                    "metadata": hit.payload.get("metadata", {})
                }
                for hit in results
            ]

            if not chunks:
                return {"chunks": []}

            if len(chunks) <= 3:
                return {"chunks": [c["content"] for c in chunks]}

            chunks_text = "\n\n".join([
                f"[{i}] {chunk['content'][:300]}"
                for i, chunk in enumerate(chunks)
            ])

            rerank_prompt = f"""Given the user question and these text chunks, rank them by relevance.
Return ONLY a JSON array of the top 3 most relevant chunk indices: [0, 2, 5]

Question: {search_query}

Chunks:
{chunks_text}

Return ONLY a JSON array of indices:"""

            rerank_response = mistral_client.chat.complete(
                model="mistral-small-2506",
                messages=[{"role": "user", "content": rerank_prompt}],
                temperature=0.1
            )

            import json
            try:
                indices = json.loads(rerank_response.choices[0].message.content)
                selected_chunks = [chunks[i]["content"] for i in indices[:3] if i < len(chunks)]
            except:
                selected_chunks = [chunks[i]["content"] for i in range(3)]

            return {"chunks": selected_chunks}

        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"chunks": []}

    return search




class RAGAgentState(BaseModel):
    messages: Annotated[List[AnyMessage], add_messages]
    search_results: List[str] = []
    n_search: int = 0
    max_searches: int = 5
    error_message: Optional[str] = None
    trim_strategy: Literal["none", "hard", "summary"] = "summary"
    max_tokens: int = 8000


class RAGAgent:
    """RAG Agent with LangGraph, PostgresSaver and advanced history management"""

    def __init__(
        self,
        user_id: str,
        conversation_id: str,
        model_name: str = "mistral-small-2506",
        summarization_model_name: str = "mistral-small-2506",
        summarization_max_tokens: int = 300,
        system_prompt: str = "",
        max_searches: int = 3,
        trim_strategy: Literal["none", "hard", "summary"] = "summary",
        max_tokens: int = 8000,
        test_mode: bool = False,
        checkpointer=None,
    ):

        self.user_id = user_id
        self.model_name = model_name
        self.max_searches = max_searches
        self.trim_strategy = trim_strategy
        self.max_tokens = max_tokens
        self.max_tokens_before_summary = int(max_tokens * 0.8)
        self.summarization_model_name = summarization_model_name
        self.summarization_max_tokens = summarization_max_tokens

        self.init_system_prompt = False
        self.mistral_client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
        self.model_name = model_name
        self.summarization_model_name = summarization_model_name

        # Create tools
        self.search_tool = create_search_tool(user_id)

        # Only add action tools (escalation, booking) if not in test mode
        if not test_mode:
            self.escalation_tool = create_escalation_tool(user_id, conversation_id)
            self.check_availability_tool = create_check_availability_tool(user_id, conversation_id)
            self.booking_tool = create_booking_tool(user_id, conversation_id)
            self.tools = [self.search_tool, self.escalation_tool, self.check_availability_tool, self.booking_tool]
        else:
            self.tools = [self.search_tool]

        self.tools_schema = [tool.args_schema.schema() if hasattr(tool, 'args_schema') else {} for tool in self.tools]
        if not system_prompt or system_prompt.strip() == "":
            from app.deps.system_prompt import SYSTEM_PROMPT

            system_prompt = SYSTEM_PROMPT
            logger.warning(
                f"[RAGAgent] No system_prompt provided for user {user_id}, using default SYSTEM_PROMPT"
            )

        self.system_prompt = [SystemMessage(content=system_prompt)]

        if checkpointer is None:
            self.checkpointer = None
        else:
            self.checkpointer = checkpointer
        self.conversation_id = conversation_id

        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build simple LangGraph workflow: question → llm → tool if needed → response"""
        graph = StateGraph(RAGAgentState)

        graph.add_node("llm", self._call_llm)
        graph.add_node("handle_tool_call", self._handle_tool_call)

        graph.set_entry_point("llm")

        graph.add_conditional_edges(
            "llm",
            self._check_tool_call,
            {
                "tool_call": "handle_tool_call",
                "end": END,
            },
        )

        graph.add_edge("handle_tool_call", "llm")

        if self.checkpointer is not None:
            logger.info(f"Compiling graph WITH checkpointer for conversation {self.conversation_id}")
            return graph.compile(checkpointer=self.checkpointer)
        else:
            logger.info(f"Compiling graph WITHOUT checkpointer for conversation {self.conversation_id}")
            return graph.compile()

    def _check_tool_call(self, state: RAGAgentState) -> str:
        """Check if LLM wants to call a tool or return final response"""
        last_message = state.messages[-1] if state.messages else None
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tool_call"
        return "end"


    def _manage_history(
        self,
        messages: List[AnyMessage],
        trim_strategy: Literal["none", "hard", "summary"],
        max_tokens: int,
    ) -> List[AnyMessage]:
        """Manage the history according to the configured strategy"""
        try:
            system_messages = [m for m in messages if isinstance(m, SystemMessage)]
            messages = [m for m in messages if not isinstance(m, SystemMessage)]

            if trim_strategy == "none":
                return []

            elif (
                trim_strategy == "hard"
                and count_tokens_approximately(messages) > max_tokens
            ):
                trimmed = trim_messages(
                    messages,
                    strategy="last",
                    token_counter=count_tokens_approximately,
                    max_tokens=max_tokens,
                    start_on="human",
                    end_on=("human", "tool"),
                    include_system=False,
                )
                new_messages = system_messages + trimmed
                return [RemoveMessage(id=REMOVE_ALL_MESSAGES)] + new_messages

            elif (
                trim_strategy == "summary"
                and count_tokens_approximately(messages)
                > self.max_tokens_before_summary
            ):
                TAIL_LENGTH = 1
                TAIL_MESSAGES = messages[-TAIL_LENGTH:]
                messages_to_summarize = trim_messages(
                    messages,
                    strategy="last",
                    token_counter=count_tokens_approximately,
                    max_tokens=self.max_tokens_before_summary,
                    start_on="human",
                    end_on=("human", "tool"),
                    include_system=False,
                )

                summary_prompt = (
                    "Summarize this conversation in the language of the conversation, "
                    "concisely but without losing key facts, decisions, TODOs.\n\n"
                    + "\n".join(
                        f"{m.__class__.__name__}: {getattr(m, 'content', '')}"
                        for m in messages_to_summarize[0:-TAIL_LENGTH]
                    )
                )

                summary_response = self.mistral_client.chat.complete(
                    model=self.summarization_model_name,
                    messages=[{"role": "user", "content": summary_prompt}],
                    max_tokens=self.summarization_max_tokens
                )
                summary_content = summary_response.choices[0].message.content

                summary_system = SystemMessage(
                    content=f"[PREVIOUS CONVERSATION SUMMARY]\n{summary_content}\n[END SUMMARY]"
                )

                new_messages = system_messages + [summary_system] + TAIL_MESSAGES

                return [RemoveMessage(id=REMOVE_ALL_MESSAGES)] + new_messages

        except Exception as e:
            return [AIMessage(content=f"Error in history management: {str(e)}")]

    def _convert_messages_to_mistral(self, messages: List[AnyMessage]) -> List[Dict[str, Any]]:
        """Convert LangChain messages to Mistral API format"""
        from langgraph.graph.message import RemoveMessage

        system_contents: List[str] = []
        ordered_messages: List[Dict[str, Any]] = []

        for msg in messages:
            if isinstance(msg, RemoveMessage):
                continue
            if isinstance(msg, SystemMessage):
                if msg.content:
                    system_contents.append(msg.content)
                continue
            if isinstance(msg, HumanMessage):
                ordered_messages.append({"role": "user", "content": msg.content})
                continue
            if isinstance(msg, AIMessage):
                content = msg.content if isinstance(msg.content, str) else json.dumps(msg.content)
                mistral_msg: Dict[str, Any] = {"role": "assistant", "content": content}
                tool_calls = getattr(msg, "tool_calls", None)
                if tool_calls:
                    normalized_calls = []
                    for tc in tool_calls:
                        if isinstance(tc, dict):
                            call_id = tc.get("id")
                            call_name = tc.get("name", "")
                            call_args = tc.get("args", {})
                        else:
                            call_id = getattr(tc, "id", None)
                            call_name = getattr(tc, "name", "")
                            call_args = getattr(tc, "args", {})
                        if not call_id:
                            call_id = f"tool_call_{uuid4().hex}"
                        normalized_calls.append(
                            {
                                "id": call_id,
                                "type": "function",
                                "function": {
                                    "name": call_name,
                                    "arguments": json.dumps(call_args or {}),
                                },
                            }
                        )
                    if normalized_calls:
                        mistral_msg["tool_calls"] = normalized_calls
                ordered_messages.append(mistral_msg)
                continue
            if isinstance(msg, ToolMessage):
                tool_entry: Dict[str, Any] = {
                    "role": "tool",
                    "content": msg.content,
                    "name": getattr(msg, "name", ""),
                }
                tool_call_id = getattr(msg, "tool_call_id", None)
                if tool_call_id:
                    tool_entry["tool_call_id"] = str(tool_call_id)
                ordered_messages.append(tool_entry)

        final_messages: List[Dict[str, Any]] = []
        if system_contents:
            combined_system = "\n\n".join(
                [content.strip() for content in system_contents if content and content.strip()]
            )
            if combined_system:
                final_messages.append({"role": "system", "content": combined_system})

        for entry in ordered_messages:
            if entry["role"] == "system":
                if final_messages and final_messages[0]["role"] == "system":
                    final_messages[0]["content"] += f"\n\n{entry.get('content', '')}"
                else:
                    final_messages.insert(0, {"role": "system", "content": entry.get("content", "")})
                continue
            final_messages.append(entry)

        if not final_messages:
            base_prompt = self.system_prompt[0].content if self.system_prompt else "You are a helpful AI assistant."
            return [{"role": "system", "content": base_prompt}]

        first_role = final_messages[0]["role"]
        if first_role not in ("system", "user"):
            base_prompt = self.system_prompt[0].content if self.system_prompt else "You are a helpful AI assistant."
            final_messages.insert(0, {"role": "system", "content": base_prompt})

        return final_messages

    def _call_llm(self, state: RAGAgentState) -> Dict[str, Any]:
        """Call Mistral API directly with tool support"""
        try:
            from langgraph.graph.message import RemoveMessage
            
            messages = state.messages.copy()
            if self.system_prompt and not self.init_system_prompt:
                self.init_system_prompt = True
                messages = self.system_prompt + messages

            trimmed_messages = self._manage_history(
                messages, self.trim_strategy, self.max_tokens
            )
            
            remove_messages = [m for m in (trimmed_messages or []) if isinstance(m, RemoveMessage)]
            llm_input = trimmed_messages if trimmed_messages else messages

            mistral_messages = self._convert_messages_to_mistral(llm_input)

            tools = []
            for tool in self.tools:
                tool_def = {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.args_schema.schema() if hasattr(tool, 'args_schema') else {}
                    }
                }
                tools.append(tool_def)

            response = self.mistral_client.chat.complete(
                model=self.model_name,
                messages=mistral_messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None
            )

            choice = response.choices[0]
            content = choice.message.content or ""
            tool_calls = []

            if choice.message.tool_calls:
                for tc in choice.message.tool_calls:
                    tool_calls.append({
                        "id": tc.id,
                        "name": tc.function.name,
                        "args": json.loads(tc.function.arguments)
                    })

            ai_message = AIMessage(content=content)
            if tool_calls:
                ai_message.tool_calls = tool_calls

            result_messages = remove_messages + [ai_message] if remove_messages else [ai_message]
            return {"messages": result_messages}

        except Exception as e:
            logger.error(f"Error in _call_llm: {e}")
            import traceback
            traceback.print_exc()
            error_msg = AIMessage(content=f"Désolé, une erreur s'est produite: {str(e)}")
            return {"messages": [error_msg]}

    def _handle_tool_call(self, state: RAGAgentState) -> Dict[str, Any]:
        """Handle the tool call"""
        try:
            last_message = state.messages[-1] if state.messages else None
            tool_calls = getattr(last_message, "tool_calls", [])
            tool_call = tool_calls[0]
            tool_name = tool_call.get("name")

            # Route to appropriate handler
            if tool_name == "search":
                return self._search(state)
            elif tool_name == "escalate_to_human":
                return self._escalate(state)
            elif tool_name == "check_availability":
                return self._check_availability(state)
            elif tool_name == "create_booking":
                return self._create_booking(state)
            else:
                return {
                    "messages": [
                        ToolMessage(
                            content=json.dumps({"error": f"Unknown tool: {tool_name}"}),
                            tool_call_id=tool_call.get("id"),
                            name=tool_call.get("name"),
                        )
                    ],
                }
        except Exception as e:
            logger.error(f"Error in _handle_tool_call: {e}")
            return {
                "messages": [AIMessage(content="Error processing tool")],
                "error_message": str(e),
            }

    def _search(self, state: RAGAgentState) -> Dict[str, Any]:
        """
        Execute unified search (parallel FAQ + documents search).
        This is an async tool, so we need to run it in an event loop.
        """
        tool_call_id = None
        tool_name = None
        tool_call = None
        
        last_message = state.messages[-1]
        tool_calls = getattr(last_message, "tool_calls", [])

        if not tool_calls:
            return {
                "messages": [
                    ToolMessage(
                        content=json.dumps({"error": "No tool calls found"}),
                        tool_call_id=None,
                        name=None,
                    )
                ],
            }

        tool_call = tool_calls[0]
        try:
            if isinstance(tool_call, dict):
                tool_name = tool_call.get("name")
                tool_call_id = tool_call.get("id")
                tool_args = tool_call.get("args", {})
            else:
                tool_name = getattr(tool_call, "name", None)
                tool_call_id = getattr(tool_call, "id", None)
                tool_args = getattr(tool_call, "args", {})
            
            if tool_call_id:
                tool_call_id = str(tool_call_id)

            if not tool_call_id:
                logger.warning("⚠️ Tool call ID not found, generating one")
                tool_call_id = f"search_{datetime.now().timestamp()}"

            logger.info(f"🔍 Executing search with args: {tool_args}")

            results = self.search_tool.invoke(tool_args)

            logger.info(f"✅ Search completed: found {len(results.get('chunks', []))} chunks")

            content = json.dumps(results, ensure_ascii=False)

            tool_message = ToolMessage(
                content=content, tool_call_id=tool_call_id, name=tool_name or "search"
            )

            return {
                "messages": [tool_message],
                "n_search": state.n_search + 1,
                "search_results": results.get("chunks", []),
            }

        except Exception as e:
            logger.error(f"❌ Error in _search: {str(e)}")
            import traceback

            traceback.print_exc()

            if not tool_call_id and tool_call:
                if isinstance(tool_call, dict):
                    tool_call_id = tool_call.get("id")
                    tool_name = tool_call.get("name")
                else:
                    tool_call_id = getattr(tool_call, "id", None)
                    tool_name = getattr(tool_call, "name", None)
            
            if tool_call_id:
                tool_call_id = str(tool_call_id)
            
            if not tool_call_id:
                tool_call_id = f"search_error_{datetime.now().timestamp()}"

            error_content = json.dumps({"error": str(e)})
            tool_message = ToolMessage(
                content=error_content, tool_call_id=tool_call_id, name=tool_name or "search"
            )
            return {
                "messages": [tool_message],
                "error_message": str(e),
            }

    def _escalate(self, state: RAGAgentState) -> Dict[str, Any]:
        """Handle escalation to human support"""
        tool_call_id = None
        tool_name = None
        tool_call = None
        
        try:
            last_message = state.messages[-1]
            tool_calls = getattr(last_message, "tool_calls", [])
            
            if not tool_calls:
                return {
                    "messages": [
                        ToolMessage(
                            content=json.dumps({"status": "error", "message": "No tool calls found"}),
                            tool_call_id=None,
                            name=None,
                        )
                    ],
                }
            
            tool_call = tool_calls[0]
            
            if isinstance(tool_call, dict):
                tool_call_id = tool_call.get("id")
                tool_name = tool_call.get("name")
                tool_args = tool_call.get("args", {})
            else:
                tool_call_id = getattr(tool_call, "id", None)
                tool_name = getattr(tool_call, "name", None)
                tool_args = getattr(tool_call, "args", {})
            
            if tool_call_id:
                tool_call_id = str(tool_call_id)
            
            if not tool_call_id:
                logger.warning("⚠️ Tool call ID not found, generating one")
                tool_call_id = f"escalate_{datetime.now().timestamp()}"

            logger.info(f"🚨 Executing escalation with args: {tool_args}")

            result = self.escalation_tool.invoke(tool_args)

            logger.info(f"✅ Escalation completed: {result}")

            tool_message = ToolMessage(
                content=json.dumps(result, ensure_ascii=False),
                tool_call_id=tool_call_id,
                name=tool_name or "escalate_to_human"
            )

            return {"messages": [tool_message]}

        except Exception as e:
            logger.error(f"❌ Error in _escalate: {str(e)}")
            import traceback
            traceback.print_exc()

            if not tool_call_id and tool_call:
                if isinstance(tool_call, dict):
                    tool_call_id = tool_call.get("id")
                    tool_name = tool_call.get("name")
                else:
                    tool_call_id = getattr(tool_call, "id", None)
                    tool_name = getattr(tool_call, "name", None)
            
            if tool_call_id:
                tool_call_id = str(tool_call_id)
            
            if not tool_call_id:
                tool_call_id = f"escalate_error_{datetime.now().timestamp()}"

            error_content = json.dumps({"status": "error", "message": str(e)})
            tool_message = ToolMessage(
                content=error_content,
                tool_call_id=tool_call_id,
                name=tool_name or "escalate_to_human"
            )
            return {"messages": [tool_message], "error_message": str(e)}

    def _check_availability(self, state: RAGAgentState) -> Dict[str, Any]:
        """Handle checking appointment availability"""
        tool_call_id = None
        tool_name = None
        tool_call = None
        
        try:
            last_message = state.messages[-1]
            tool_calls = getattr(last_message, "tool_calls", [])
            
            if not tool_calls:
                return {
                    "messages": [
                        ToolMessage(
                            content=json.dumps({"available_slots": [], "count": 0, "error": "No tool calls found"}),
                            tool_call_id=None,
                            name=None,
                        )
                    ],
                }
            
            tool_call = tool_calls[0]
            
            if isinstance(tool_call, dict):
                tool_call_id = tool_call.get("id")
                tool_name = tool_call.get("name")
                tool_args = tool_call.get("args", {})
            else:
                tool_call_id = getattr(tool_call, "id", None)
                tool_name = getattr(tool_call, "name", None)
                tool_args = getattr(tool_call, "args", {})
            
            if tool_call_id:
                tool_call_id = str(tool_call_id)
            
            if not tool_call_id:
                logger.warning("⚠️ Tool call ID not found, generating one")
                tool_call_id = f"check_availability_{datetime.now().timestamp()}"

            logger.info(f"📅 Checking availability with args: {tool_args}")

            result = self.check_availability_tool.invoke(tool_args)

            logger.info(f"✅ Availability check completed: found {result.get('count', 0)} slots")

            tool_message = ToolMessage(
                content=json.dumps(result, ensure_ascii=False),
                tool_call_id=tool_call_id,
                name=tool_name or "check_availability"
            )

            return {"messages": [tool_message]}

        except Exception as e:
            logger.error(f"❌ Error in _check_availability: {str(e)}")
            import traceback
            traceback.print_exc()

            if not tool_call_id and tool_call:
                if isinstance(tool_call, dict):
                    tool_call_id = tool_call.get("id")
                    tool_name = tool_call.get("name")
                else:
                    tool_call_id = getattr(tool_call, "id", None)
                    tool_name = getattr(tool_call, "name", None)
            
            if tool_call_id:
                tool_call_id = str(tool_call_id)
            
            if not tool_call_id:
                tool_call_id = f"check_availability_error_{datetime.now().timestamp()}"

            error_content = json.dumps({"available_slots": [], "count": 0, "error": str(e)})
            tool_message = ToolMessage(
                content=error_content,
                tool_call_id=tool_call_id,
                name=tool_name or "check_availability"
            )
            return {"messages": [tool_message], "error_message": str(e)}

    def _create_booking(self, state: RAGAgentState) -> Dict[str, Any]:
        """Handle creating an appointment booking"""
        tool_call_id = None
        tool_name = None
        tool_call = None
        
        try:
            last_message = state.messages[-1]
            tool_calls = getattr(last_message, "tool_calls", [])
            
            if not tool_calls:
                return {
                    "messages": [
                        ToolMessage(
                            content=json.dumps({"status": "error", "message": "No tool calls found"}),
                            tool_call_id=None,
                            name=None,
                        )
                    ],
                }
            
            tool_call = tool_calls[0]
            
            if isinstance(tool_call, dict):
                tool_call_id = tool_call.get("id")
                tool_name = tool_call.get("name")
                tool_args = tool_call.get("args", {})
            else:
                tool_call_id = getattr(tool_call, "id", None)
                tool_name = getattr(tool_call, "name", None)
                tool_args = getattr(tool_call, "args", {})
            
            if tool_call_id:
                tool_call_id = str(tool_call_id)
            
            if not tool_call_id:
                logger.warning("⚠️ Tool call ID not found, generating one")
                tool_call_id = f"create_booking_{datetime.now().timestamp()}"

            logger.info(f"📅 Creating booking with args: {tool_args}")

            result = self.booking_tool.invoke(tool_args)

            logger.info(f"✅ Booking creation completed: {result}")

            tool_message = ToolMessage(
                content=json.dumps(result, ensure_ascii=False),
                tool_call_id=tool_call_id,
                name=tool_name or "create_booking"
            )

            return {"messages": [tool_message]}

        except Exception as e:
            logger.error(f"❌ Error in _create_booking: {str(e)}")
            import traceback
            traceback.print_exc()

            if not tool_call_id and tool_call:
                if isinstance(tool_call, dict):
                    tool_call_id = tool_call.get("id")
                    tool_name = tool_call.get("name")
                else:
                    tool_call_id = getattr(tool_call, "id", None)
                    tool_name = getattr(tool_call, "name", None)
            
            if tool_call_id:
                tool_call_id = str(tool_call_id)
            
            if not tool_call_id:
                tool_call_id = f"create_booking_error_{datetime.now().timestamp()}"

            error_content = json.dumps({"status": "error", "message": str(e)})
            tool_message = ToolMessage(
                content=error_content,
                tool_call_id=tool_call_id,
                name=tool_name or "create_booking"
            )
            return {"messages": [tool_message], "error_message": str(e)}

    async def process_message(self, message: str) -> Dict[str, Any]:
        """
        Process a message through the RAG agent and return the response.
        
        Args:
            message: The user's message content
            
        Returns:
            dict with:
            - response: The AI's response text
            - intent: Detected intent (optional)
            - confidence: Confidence score (optional)
            - sources: List of sources used (optional)
            - escalated: Whether conversation was escalated (optional)
        """
        try:
            logger.info(f"Processing message for conversation {self.conversation_id}, checkpointer={self.checkpointer}")
            
            config = None
            if self.checkpointer is not None:
                config = {"configurable": {"thread_id": self.conversation_id}}
            
            initial_state = {
                "messages": self.system_prompt + [HumanMessage(content=message)],
                "n_search": 0,
                "search_results": [],
            }
            
            logger.info(f"Invoking graph with config={config is not None}, checkpointer={self.checkpointer is not None}")
            
            if self.checkpointer is not None:
                def run_sync():
                    return self.graph.invoke(initial_state, config=config)
                result = await asyncio.to_thread(run_sync)
            else:
                result = await self.graph.ainvoke(initial_state)
            
            last_message = result.get("messages", [])[-1] if result.get("messages") else None
            
            if isinstance(last_message, AIMessage):
                response_text = last_message.content
            else:
                response_text = str(last_message) if last_message else "Désolé, je n'ai pas pu générer de réponse."
            
            escalated = False
            for msg in result.get("messages", []):
                if isinstance(msg, ToolMessage) and "escalate" in msg.content.lower():
                    escalated = True
                    break
            return {
                "response": response_text,
                "intent": "general",
                "confidence": 0.8,
                "sources": result.get("search_results", []),
                "escalated": escalated,
            }
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            import traceback
            traceback.print_exc()
            return {
                "response": f"Erreur lors du traitement: {str(e)}",
                "intent": "error",
                "confidence": 0.0,
                "sources": [],
                "escalated": False,
            }


def create_rag_agent(
    user_id: str,
    conversation_id: str,
    summarization_model_name: Optional[str] = None,
    summarization_max_tokens: int = 350,
    model_name: Optional[str] = None,
    max_searches: int = 3,
    system_prompt: Optional[str] = None,
    trim_strategy: Literal["none", "hard", "summary"] = "summary",
    max_tokens: Optional[int] = None,
    test_mode: bool = False,
    checkpointer=None,
) -> RAGAgent:
    """Factory function to create a RAG Agent with settings from database"""
    ai_settings = get_ai_settings_from_db(user_id)

    final_model_name = model_name or ai_settings["model_name"]
    final_system_prompt = system_prompt if system_prompt else ai_settings["system_prompt"]
    final_summarization_model_name = summarization_model_name or ai_settings["model_name"]
    final_max_tokens = max_tokens if max_tokens else ai_settings["max_tokens"]

    # Fetch FAQs from database and append to system prompt
    try:
        db = get_db()
        faqs_result = db.table("faqs").select("*").eq("user_id", user_id).execute()

        if faqs_result.data and len(faqs_result.data) > 0:
            faq_context = "\n\n=== FAQ (Questions Fréquentes) ===\n"
            for faq in faqs_result.data:
                faq_context += f"\nQuestion: {faq['question']}\n"

                # Add variants if they exist
                if faq.get('variants') and len(faq['variants']) > 0:
                    variants_str = ", ".join(faq['variants'])
                    faq_context += f"Variantes: {variants_str}\n"

                faq_context += f"Réponse: {faq['answer']}\n"

                # Add category if available
                if faq.get('category'):
                    faq_context += f"Catégorie: {faq['category']}\n"

            final_system_prompt += faq_context
            logger.info(f"Added {len(faqs_result.data)} FAQs to system prompt")
    except Exception as e:
        logger.error(f"Error loading FAQs for system prompt: {e}")

    # Add current date to system prompt
    current_date = datetime.now().strftime("%Y-%m-%d")
    date_context = f"\n\n=== Date Actuelle ===\nAujourd'hui nous sommes le: {current_date}\n"
    final_system_prompt += date_context

    logger.info(f"Creating RAG agent with settings: model={final_model_name}, system_prompt_length={len(final_system_prompt)}")

    return RAGAgent(
        user_id=user_id,
        conversation_id=conversation_id,
        model_name=final_model_name,
        max_searches=max_searches,
        trim_strategy=trim_strategy,
        summarization_model_name=final_summarization_model_name,
        summarization_max_tokens=summarization_max_tokens,
        max_tokens=final_max_tokens,
        system_prompt=final_system_prompt,
        checkpointer=checkpointer,
        test_mode=test_mode,
    )


if __name__ == "__main__":
    # Import uniquement pour les tests (évite de bloquer le démarrage du backend)
    from app.deps.runtime_prod import CHECKPOINTER_POSTGRES

    agent = create_rag_agent(
        user_id="example_user_id",
        conversation_id="example_conversation_id",
        system_prompt="You are a helpful assistant that can answer questions and help with tasks.",
        trim_strategy="summary",
        max_tokens=6000,
        checkpointer=CHECKPOINTER_POSTGRES,
        test_mode=True,
    )

    print("Accès au graphique...")
    graph = agent.graph.get_graph()

    print("Génération du code Mermaid...")
    try:
        mermaid_code = graph.draw_mermaid()
        print("Code Mermaid généré avec succès!")
        print("Longueur du code:", len(mermaid_code), "caractères")

        with open("/workspace/rag_agent_graph.mmd", "w", encoding="utf-8") as f:
            f.write(mermaid_code)
        print("Code Mermaid sauvegardé dans /workspace/rag_agent_graph.mmd")

        print("\nPremières lignes du code Mermaid:")
        print("=" * 50)
        lines = mermaid_code.split("\n")
        for i, line in enumerate(lines[:20]):
            print(f"{i+1:2d}: {line}")
        if len(lines) > 20:
            print(f"... et {len(lines) - 20} lignes supplémentaires")

    except Exception as e:
        print(f"Erreur lors de la génération du code Mermaid: {e}")
        import traceback

        traceback.print_exc()
