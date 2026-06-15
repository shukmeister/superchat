"""Fusion chat flow manager.

This module manages the fusion chat flow: a panel of models answers each user
message in parallel and blind to one another, then a single fusion model acts as
both judge (structured comparison of the panel answers) and synthesizer (writes
the final answer from that comparison).

Key responsibilities:
- Fan the user's message out to all panel agents in parallel
- Display each panel answer transparently
- Run the judge call (structured analysis) and display it
- Run the synthesis call (final answer) and display it
- Track which fused answers have been produced for cross-turn continuity
- Aggregate token usage across all calls into the session stats

Unlike the staged flow there is no cross-turn phase machine: every user message
runs the full panel -> judge -> synthesis pipeline start to finish.
"""

import asyncio
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from halo import Halo
from superchat.utils.stats import extract_usage_from_task_result


class FusionFlowManager:
    """Manages fusion chat flow: parallel blind panel + judge/synthesizer."""

    def __init__(self, config, panel_agents, judge_agent, synth_agent,
                 message_handler, agent_model_mapping):
        """Initialize fusion flow manager with chat components.

        Args:
            config: SessionConfig instance
            panel_agents: List of AutoGen agents that answer in parallel (blind)
            judge_agent: AutoGen agent that produces the structured analysis
            synth_agent: AutoGen agent that writes the final answer
            message_handler: MessageHandler instance (reused for formatting/errors)
            agent_model_mapping: Dict mapping panel agent names to model info
        """
        self.config = config
        self.panel_agents = panel_agents
        self.judge_agent = judge_agent
        self.synth_agent = synth_agent
        self.message_handler = message_handler
        self.agent_model_mapping = agent_model_mapping
        self.fusion_model = config.get_fusion_model()

        # Cross-turn memory: only the user prompt + final fused answer of each turn
        self.fused_history = []

    # Run the full fusion pipeline for one user message
    async def handle_message(self, message):
        """Fan out to the panel, judge the answers, synthesize the final answer."""
        # Track panel and synthesizer (judge + synth) usage separately so each is
        # priced at the correct model's rate
        panel_usage = []
        synth_usage = []

        # 1. Panel fan-out (parallel, blind to each other)
        panel_responses = await self._run_panel(message, panel_usage)
        if not panel_responses:
            # Every panel member failed - nothing to judge or synthesize
            return

        # Display each panel answer in slot order
        for resp in panel_responses:
            header = self.message_handler._format_agent_display(resp['identifier'], resp['model_name'])
            print(f"{header}\n> {resp['text']}\n")

        panel_block = self._format_panel_block(panel_responses)

        # 2. Judge call (structured analysis). Degrades gracefully to no analysis.
        analysis = await self._run_judge(message, panel_block, synth_usage)
        if analysis:
            print("Judge analysis:")
            print(f"> {analysis}\n")
        else:
            print("Judge analysis unavailable - synthesizing directly from panel answers.\n")

        # 3. Synthesis call (final answer)
        fused_answer = await self._run_synthesizer(message, panel_block, analysis, synth_usage)
        if fused_answer:
            label = self.message_handler.model_client_manager.get_model_label(self.fusion_model)
            print(f"[⊕] \033[4m{label}\033[0m (fusion):")
            print(f"> {fused_answer}\n")
            self.fused_history.append({'prompt': message, 'answer': fused_answer})

        # 4. Record usage: one conversation round, with synth tokens tracked separately
        self._record_usage(panel_usage, synth_usage)

    # Fan the message out to all panel agents in parallel, collecting responses
    async def _run_panel(self, message, usage_results):
        """Run every panel agent concurrently. Returns list of response dicts (slot order)."""
        async def run_one(agent):
            new_message = TextMessage(content=message, source="user")
            return await agent.run(task=[new_message])

        with Halo(text="Querying panel", spinner="dots"):
            results = await asyncio.gather(
                *[run_one(agent) for agent in self.panel_agents],
                return_exceptions=True
            )

        panel_responses = []
        for i, (agent, result) in enumerate(zip(self.panel_agents, results)):
            info = self.agent_model_mapping.get(agent.name, {})
            model_name = info.get('model_name', 'unknown')
            identifier = info.get('identifier', '?')

            if isinstance(result, Exception):
                # Surface known OpenRouter errors cleanly; otherwise note the failure
                if not self.message_handler._handle_openrouter_error(result):
                    label = self.message_handler.model_client_manager.get_model_label(model_name)
                    print(f"[{identifier}] {label} failed to respond: {result}\n")
                continue

            usage = extract_usage_from_task_result(result)
            if usage:
                usage_results.append(usage)

            panel_responses.append({
                'identifier': identifier,
                'model_name': model_name,
                'text': self.message_handler._get_response_from_task_result(result)
            })

        return panel_responses

    # Run the judge agent to produce a structured comparison of the panel answers
    async def _run_judge(self, message, panel_block, usage_results):
        """Return the analysis text, or None if the judge call failed/was empty."""
        await self.judge_agent.on_reset(CancellationToken())

        judge_task = (
            f"Question:\n{message}\n\n"
            f"Independent answers from the panel:\n\n{panel_block}\n\n"
            f"Produce your structured comparison."
        )

        try:
            with Halo(text="Judging", spinner="dots"):
                result = await self.judge_agent.run(task=judge_task)
        except Exception as e:
            if not self.message_handler._handle_openrouter_error(e):
                print(f"Judge call failed: {e}\n")
            return None

        usage = extract_usage_from_task_result(result)
        if usage:
            usage_results.append(usage)

        analysis = self.message_handler._get_response_from_task_result(result)
        if not analysis or analysis == "No response received":
            return None
        return analysis

    # Run the synthesizer agent to write the final answer
    async def _run_synthesizer(self, message, panel_block, analysis, usage_results):
        """Return the fused answer text, or None if the synthesis call failed."""
        await self.synth_agent.on_reset(CancellationToken())

        parts = []
        if self.fused_history:
            history_lines = []
            for exchange in self.fused_history:
                history_lines.append(
                    f"Earlier question: {exchange['prompt']}\n"
                    f"Your earlier answer: {exchange['answer']}"
                )
            parts.append("Prior conversation (your earlier fused answers):\n" + "\n\n".join(history_lines))

        parts.append(f"Current question:\n{message}")
        if analysis:
            parts.append(f"Structured analysis of the panel's answers:\n{analysis}")
        else:
            parts.append("No structured analysis is available; rely on the panel answers directly.")
        parts.append(f"The panel's answers:\n\n{panel_block}")
        parts.append("Write the single best answer to the current question.")
        synth_task = "\n\n".join(parts)

        try:
            with Halo(text="Synthesizing", spinner="dots"):
                result = await self.synth_agent.run(task=synth_task)
        except Exception as e:
            if not self.message_handler._handle_openrouter_error(e):
                print(f"Synthesis call failed: {e}\n")
            return None

        usage = extract_usage_from_task_result(result)
        if usage:
            usage_results.append(usage)

        answer = self.message_handler._get_response_from_task_result(result)
        if not answer or answer == "No response received":
            return None
        return answer

    # Format the panel responses into a labeled block for the judge/synth prompts
    def _format_panel_block(self, panel_responses):
        """Build a labeled, blank-line-separated block of all panel answers."""
        blocks = []
        for resp in panel_responses:
            label = self.message_handler.model_client_manager.get_model_label(resp['model_name'])
            blocks.append(f"[{resp['identifier']}] {label}:\n{resp['text']}")
        return "\n\n".join(blocks)

    # Aggregate usage and record a single conversation round
    def _record_usage(self, panel_usage, synth_usage):
        """Add one round to stats; track the synthesizer's portion separately for costing."""
        all_usage = panel_usage + synth_usage
        if not all_usage:
            return

        # Totals (panel + judge + synth) count as one conversation round
        self.config.add_usage_data(self._sum_usage(all_usage))

        # Synthesizer-side tokens (judge + synth) are priced at the fusion model's rate
        if synth_usage:
            self.config.add_fusion_synth_usage(self._sum_usage(synth_usage))

    # Sum a list of usage dicts into a single combined dict
    def _sum_usage(self, usage_list):
        """Combine a list of {prompt,completion,total}_tokens dicts."""
        combined = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        for usage in usage_list:
            combined["prompt_tokens"] += usage.get("prompt_tokens", 0)
            combined["completion_tokens"] += usage.get("completion_tokens", 0)
            combined["total_tokens"] += usage.get("total_tokens", 0)
        return combined
