from typing import Any, Callable, Dict, List, Optional

from agents import (
  WebSearchTool,
  Agent,
  ModelSettings,
  TResponseInputItem,
  Runner,
  RunConfig,
  RawResponsesStreamEvent,
  RunItemStreamEvent,
  AgentUpdatedStreamEvent,
)
from openai.types.shared.reasoning import Reasoning
from pydantic import BaseModel

# Tool definitions
web_search_preview = WebSearchTool(
  user_location={
    "type": "approximate",
    "country": None,
    "region": None,
    "city": None,
    "timezone": None
  },
  search_context_size="medium"
)

life_care_planner = Agent(
  name="Life Care planner",
  instructions="""You are an expert life care planner. Review the provided patient history and injury details to fully understand the patient's condition and needs. Your task is to create a well-considered list of recommendations for the patient, organized into four categories: home modifications, durable medical equipment, medications, and therapeutic modalities. For each category, list the specific items or services you suggest the patient should consider or research, based on their condition. 

# Output Format

Output your recommendations as a JSON object, where each of the four categories is a key, and the value is a list of item or service names relevant for that category. For example:

{
  \"home_modifications\": [ \"ramps\", \"bathroom grab bars\", \"widened doorways\" ],
  \"durable_medical_equipment\": [ \"power wheelchair\", \"hospital bed\" ],
  \"medications\": [ \"baclofen\", \"gabapentin\" ],
  \"therapeutic_modalities\": [ \"physical therapy\", \"occupational therapy\" ]
}

Only include items and services appropriate to the specifics of the patient's case, as derived from the input provided. If a category does not apply, return an empty list for that category.""",
  model="gpt-5-mini",
  model_settings=ModelSettings(
    store=True,
    reasoning=Reasoning(
      effort="medium",
      summary="auto"
    )
  )
)

cost_research = Agent(
  name="Cost Research",
  instructions="""Act as a cost research assistant for a life care planner. Given a JSON input organized by item category (e.g., home_modifications, durable_medical_equipment, medications, therapeutic_modalities), use web search tools and specific recommended sources to perform detailed cost analysis for each item, appending a sub-JSON to each item entry that includes the following fields:

- price (numerical, in USD)
- replacement_frequency (a clear interval or note indicating expected replacement/renewal)
- cpt_code (if applicable; leave blank if not relevant)
- sources(a URL indicating where you found the data; prioritize URLs from recommended sites when appropriate)

**Web Search Priorities**
- For medication costs, prioritize data from goodrx.com and costplusdrugs.com.
- For medical equipment, prioritize medmartonline.com.
- Use general web search for other items, seeking reputable sources.
- If a direct CPT code cannot be found, leave the field blank.

**Methodology**
- For each item, before fetching results or outputting an answer, explicitly reason step-by-step about:
    - Which source(s) to use
    - How you are interpreting the item description and category
    - How you determined/estimated cost and replacement interval
    - How you located or verified the CPT code (if any)
- After reasoning, list the researched price, replacement frequency, CPT code (or blank), and sources as output fields appended to that item.
- Persist with each item until all necessary information is located or determined best-effort.
- Proceed item by item, category by category, until the full input JSON is covered and enhanced per schema.

**Output Format**
- Return a single JSON object in the provided schema, with each original item expanded to include price, replacement_frequency, cpt_code, and sources (see below).
- The entire output must conform strictly to the provided JSON schema; do not use markdown, code blocks, or commentary in your response.
- All prices must be in USD numerals; cite multiple sources where possible.
-- Use only real URLs from the sources returned by the web search tool and include the full working URL.
- The required output resembles:
{
  \"home_modifications\": [
    {
      \"item_name\": \"[item name]\",
      \"price\": [numeric price],
      \"replacement_frequency\": \"[interval]\",
      \"cpt_code\": \"[string or blank]\",
      \"sources\": [\"[URL1]\", \"[URL2]\"]
    }
    // ... additional items
  ],
  \"durable_medical_equipment\": [
    // ... structure as above
  ],
  \"medications\": [
    // ... structure as above
  ],
  \"therapeutic_modalities\": [
    // ... structure as above
  ]
}

**Example (using placeholders):**

Example reasoning (attached to first item, not output, but guide for you):

- \"Reasoning: The item is [medication], so I check goodrx.com and costplusdrugs.com, using search terms '[medication] price'. Interpreted as a 30-day supply. No CPT code is needed for medications. Use both sites’ main URLs for citation.\"
- Conclusion:
  {
    \"item_name\": \"[Aspirin 81mg tablets]\",
    \"price\": 7.99,
    \"replacement_frequency\": \"30 days\",
    \"cpt_code\": \"\",
    \"sources\": [\"https://www.goodrx.com/aspirin\", \"https://www.costplusdrugs.com/medications/aspirin-81mg/\"]
  }

(Real examples will be longer and may include more sources and realistic replacement frequencies or blank CPT fields.)

**Edge Cases and Special Instructions**
- If unable to determine a price or replacement interval, estimate based on available sources and state the basis in your internal reasoning (not in the output).
- For CPT codes, only include if directly relevant and verifiable from reliable public sources.
- All output must be a single valid JSON object matching the provided schema without code fencing or added notes.

---

**REMINDER:**  
You are performing detailed, step-by-step research reasoning before output, but only the final JSON conforming to the schema is to be output—no explanations, markdown, or notes.  When finding sources, you must only include URLs that you have verified exist in actual search results.
Never fabricate or guess URLs.All fields must be filled to the best of your researched ability; ensure price, frequency, and source(s) are provided for every item.""",
  model="gpt-5",
  tools=[
    web_search_preview
  ],
  model_settings=ModelSettings(
    store=True,
    reasoning=Reasoning(
      effort="medium",
      summary="auto"
    )
  )
)

TRACE_METADATA: Dict[str, str] = {
  "__trace_source__": "agent-builder",
  "workflow_id": "wf_68e546b99b648190846e2b394cac992e0751bac17b50f2e0"
}


class WorkflowInput(BaseModel):
  input_as_text: str


def _build_initial_conversation(workflow_input: WorkflowInput) -> List[TResponseInputItem]:
  workflow = workflow_input.model_dump()
  return [
    {
      "role": "user",
      "content": [
        {
          "type": "input_text",
          "text": workflow["input_as_text"]
        }
      ]
    }
  ]


def _emit(callback: Optional[Callable[[Dict[str, Any]], None]], payload: Dict[str, Any]) -> None:
  if callback:
    callback(payload)


def _extract_message_text(raw_message: Any) -> str:
  if not raw_message or not hasattr(raw_message, "content"):
    return ""
  parts: List[str] = []
  for part in getattr(raw_message, "content", []):
    text = getattr(part, "text", None)
    if text:
      parts.append(text)
  return "\n".join(parts).strip()


def _convert_stream_event(stage: str, event: Any) -> List[Dict[str, Any]]:
  payloads: List[Dict[str, Any]] = []

  if isinstance(event, RawResponsesStreamEvent):
    raw = event.data
    event_type = getattr(raw, "type", "")
    text_delta = getattr(raw, "delta", None)
    if isinstance(text_delta, str):
      if "reasoning" in event_type:
        payloads.append({
          "stage": stage,
          "type": "reasoning_delta",
          "content": text_delta
        })
      elif event_type == "response.output_text.delta":
        payloads.append({
          "stage": stage,
          "type": "output_delta",
          "content": text_delta
        })

  elif isinstance(event, RunItemStreamEvent):
    if event.name == "tool_called":
      call_type = getattr(event.item.raw_item, "type", "tool_call")
      payloads.append({
        "stage": stage,
        "type": "tool_call",
        "content": str(call_type)
      })
    elif event.name == "tool_output":
      output_repr = getattr(event.item, "output", None)
      if isinstance(output_repr, str) and len(output_repr) > 200:
        output_repr = f"{output_repr[:197]}..."
      elif output_repr is None:
        output_repr = getattr(event.item.raw_item, "status", "completed")
      payloads.append({
        "stage": stage,
        "type": "tool_output",
        "content": str(output_repr)
      })
    elif event.name == "message_output_created":
      message_text = _extract_message_text(event.item.raw_item)
      if message_text:
        payloads.append({
          "stage": stage,
          "type": "message",
          "content": message_text
        })

  elif isinstance(event, AgentUpdatedStreamEvent):
    payloads.append({
      "stage": stage,
      "type": "agent_updated",
      "content": event.new_agent.name
    })

  return payloads


async def _run_stage_stream(
  agent: Agent,
  stage_name: str,
  conversation_history: List[TResponseInputItem],
  callback: Optional[Callable[[Dict[str, Any]], None]],
) -> str:
  _emit(callback, {
    "stage": stage_name,
    "type": "stage_start",
    "content": f"{agent.name} starting"
  })

  result_stream = Runner.run_streamed(
    agent,
    input=[*conversation_history],
    run_config=RunConfig(trace_metadata=TRACE_METADATA),
  )

  try:
    async for event in result_stream.stream_events():
      for payload in _convert_stream_event(stage_name, event):
        _emit(callback, payload)
  except Exception as exc:
    _emit(callback, {
      "stage": stage_name,
      "type": "stage_error",
      "content": str(exc)
    })
    raise

  final_output: str = ""
  if result_stream.final_output is not None:
    try:
      final_output = result_stream.final_output_as(str)
    except TypeError:
      final_output = str(result_stream.final_output)

  _emit(callback, {
    "stage": stage_name,
    "type": "stage_complete",
    "content": f"{agent.name} finished"
  })

  conversation_history.extend([item.to_input_item() for item in result_stream.new_items])
  return final_output


async def run_workflow(workflow_input: WorkflowInput) -> str:
  conversation_history = _build_initial_conversation(workflow_input)

  life_care_planner_result = await Runner.run(
    life_care_planner,
    input=[*conversation_history],
    run_config=RunConfig(trace_metadata=TRACE_METADATA)
  )
  conversation_history.extend([item.to_input_item() for item in life_care_planner_result.new_items])

  cost_research_result = await Runner.run(
    cost_research,
    input=[*conversation_history],
    run_config=RunConfig(trace_metadata=TRACE_METADATA)
  )
  conversation_history.extend([item.to_input_item() for item in cost_research_result.new_items])

  return cost_research_result.final_output_as(str)


async def stream_workflow(
  workflow_input: WorkflowInput,
  callback: Optional[Callable[[Dict[str, Any]], None]] = None
) -> str:
  conversation_history = _build_initial_conversation(workflow_input)

  planner_output = await _run_stage_stream(
    life_care_planner,
    "planner",
    conversation_history,
    callback,
  )
  _emit(callback, {
    "stage": "planner",
    "type": "stage_output",
    "content": planner_output
  })

  cost_output = await _run_stage_stream(
    cost_research,
    "cost_research",
    conversation_history,
    callback,
  )
  _emit(callback, {
    "stage": "cost_research",
    "type": "stage_output",
    "content": cost_output
  })

  _emit(callback, {
    "stage": "final",
    "type": "stage_complete",
    "content": "Workflow finished"
  })

  return cost_output
