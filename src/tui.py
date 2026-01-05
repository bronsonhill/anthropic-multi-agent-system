from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Static, Button, RichLog, ProgressBar, Label, Input
from textual.binding import Binding
from textual import work
from datetime import datetime
import asyncio
import json
from claude_agent_sdk import query, AssistantMessage, UserMessage, ResultMessage
from agents.orchestrator import ResearchLeadAgent

class SubAgentPanel(Static):
    """Panel for a sub-agent status."""
    def compose(self) -> ComposeResult:
        with Vertical(classes="subagent-inner"):
            yield Label("Idle", id=f"status-{self.id}")
            yield RichLog(id=f"log-{self.id}", wrap=True, highlight=True, markup=True)

    def update_status(self, status: str):
        try:
            self.query_one(f"#status-{self.id}", Label).update(status)
        except:
            pass

    def log_activity(self, message: str):
        try:
            # Check if mounted or if we can write
            log_widget = self.query_one(f"#log-{self.id}", RichLog)
            log_widget.write(message)
        except:
            pass

class ResearchDashboard(App):
    CSS = """
    Screen {
        layout: grid;
        grid-size: 2;
        grid-columns: 2fr 1fr;
        grid-rows: 1fr 3fr;
    }

    .panel {
        background: $surface;
        border: solid $primary;
        padding: 1;
        margin: 1;
    }

    #left-panel {
        row-span: 2;
        width: 100%;
        height: 100%;
        border-title-align: center;
        border: round $accent;
    }

    #right-panel {
        row-span: 2;
        width: 100%;
        height: 100%;
        layout: vertical;
        border: round $success;
    }

    #bottom-panel {
        column-span: 2;
        height: auto;
        dock: bottom;
        background: $surface-darken-1;
        padding: 1;
    }

    .subagent-box {
        height: auto;
        min-height: 15;
        border: solid $secondary;
        margin-bottom: 1;
        background: $surface-lighten-1;
    }
    
    .subagent-inner {
        padding: 1;
    }

    #progress-bar {
        width: 1fr;
    }

    .metric {
        margin-left: 2;
        content-align: center middle;
    }
    
    #input-container {
        dock: top;
        padding: 1;
        height: auto;
    }
    """

    TITLE = "Research Team Dashboard"
    SUB_TITLE = "Multi-Agent Orchestrator"
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "start_research", "Start Research"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        
        # Input for research task
        with Container(id="input-container"):
            yield Input(placeholder="Enter research topic...", id="research-input")
            yield Button("Start Research", id="start-btn", variant="primary")

        # Main Layout
        with Vertical(id="left-panel", classes="panel"):
            yield Label("Lead Agent Thinking Process", classes="panel-title")
            yield RichLog(id="lead-log", markup=True, wrap=True)

        with Vertical(id="right-panel", classes="panel"):
            yield Label("Sub-Agents Status", classes="panel-title")
            yield VerticalScroll(id="subagents-container")

        with Horizontal(id="bottom-panel"):
            yield ProgressBar(id="progress-bar", total=100, show_eta=False)
            yield Label("Tokens: 0", id="token-counter", classes="metric")
            yield Label("Cost: $0.0000", id="cost-counter", classes="metric")

        yield Footer()

    def on_mount(self):
        self.query_one("#lead-log").write("[bold green]System Ready. Enter a topic and press Start or 'r'.[/]")
        self.subagent_map = {} # Maps tool_use_id to subagent widget ID

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "start-btn":
            self.action_start_research()

    async def action_start_research(self):
        topic = self.query_one("#research-input", Input).value
        if not topic:
            self.query_one("#lead-log").write("[bold red]Please enter a topic![/]")
            return

        self.query_one("#start-btn").disabled = True
        self.query_one("#lead-log").write(f"[bold yellow]Starting research on: {topic}[/]")
        self.query_one("#progress-bar", ProgressBar).update(total=None) # Indeterminate mode
        
        self.run_research_worker(topic)

    def format_tool_input(self, tool_input: dict) -> str:
        """Pretty print tool input"""
        try:
            return json.dumps(tool_input, indent=2)
        except:
            return str(tool_input)

    @work(exclusive=True, thread=True)
    async def run_research_worker(self, topic: str):
        agent = ResearchLeadAgent()
        
        total_tokens = 0
        total_cost = 0.0
        
        try:
            async for message in query(prompt=topic, options=agent.options):
                if isinstance(message, AssistantMessage):
                    if message.error:
                        self.log_lead(f"[bold red]Error: {message.error}[/]")
                    
                    # Handle delegation routing if this message belongs to a child process
                    parent_id = message.parent_tool_use_id
                    target_log_func = self.log_lead # Default to lead
                    
                    if parent_id and parent_id in self.subagent_map:
                         # This needs to go to subagent
                         target_log_func = lambda msg: self.log_subagent(parent_id, msg)

                    for block in message.content:
                        if hasattr(block, "text") and block.text:
                            target_log_func(f"[cyan]Content:[/cyan] {block.text}")
                        
                        elif hasattr(block, "thinking") and block.thinking:
                            target_log_func(f"[dim]Thinking: {block.thinking}[/dim]")
                        
                        elif hasattr(block, "name"): # Tool Call
                            tool_name = block.name
                            tool_input = block.input
                            
                            formatted_input = self.format_tool_input(tool_input)
                            
                            # Special handling for delegation tool
                            if tool_name == "web_researcher_agents" or tool_name == "Task":
                                # This is a Delegation event (Lead -> Subagent)
                                # Initialize the subagent panel
                                self.update_subagent_task(block.id, tool_input, "Running")
                                # Log to lead that we started it, but keep it brief
                                self.log_lead(f"[magenta]Orchestrator Delegating Task -> Sub-Agent[/magenta]")
                            
                            else:
                                # Normal tool call
                                log_msg = f"[magenta]Tool Call: {tool_name}[/magenta]\n[dim]{formatted_input}[/dim]"
                                target_log_func(log_msg)
                                
                elif isinstance(message, UserMessage):
                     for block in message.content:
                        if hasattr(block, "tool_use_id"):
                             # Tool result returned
                             # Check if this tool result belongs to a subagent
                             # Unfortunately UserMessage doesn't trivially map back to parent tool use id in this SDK context
                             # unless we track every tool call ID. 
                             # However, for the 'complete_task' or generic results, we want to capture them.
                             
                             # If this is the result of the 'web_researcher_agents' call itself:
                             self.complete_subagent_task(block.tool_use_id, block.content)
                             
                             # If this is a result of a tool called BY a subagent (e.g. WebSearch result), 
                             # we might want to display it in the subagent panel.
                             # But we lack the 'parent_tool_use_id' here easily.
                             # We'll skip complex mapping for UserMessage for now unless we build a global map of all tool_ids -> parents.
                             
                        elif hasattr(block, "text"):
                            pass

                elif isinstance(message, ResultMessage):
                    if message.usage:
                        tokens = message.usage.get('total_tokens', 0)
                        total_tokens += tokens
                        self.update_metrics(total_tokens, total_cost)
                    
                    if message.total_cost_usd:
                        total_cost += message.total_cost_usd
                        self.update_metrics(total_tokens, total_cost)
                        
        except Exception as e:
            self.log_lead(f"[bold red]Exception: {str(e)}[/]")
            import traceback
            self.log_lead(traceback.format_exc())
            
        self.dashboard_safe_update()

    def dashboard_safe_update(self):
        def update_ui():
            self.query_one("#start-btn").disabled = False
            self.query_one("#progress-bar", ProgressBar).update(total=100, progress=100)
            self.query_one("#lead-log").write("[bold green]Research Task Completed.[/]")
        self.call_from_thread(update_ui)

    def log_lead(self, text: str):
        self.call_from_thread(self.query_one("#lead-log").write, text)
        
    def log_subagent(self, tool_id: str, text: str):
        # Log to specific subagent panel
        if tool_id in self.subagent_map:
            slot_id = self.subagent_map[tool_id]
            def update_ui():
                try:
                    widget = self.query_one(f"#{slot_id}", SubAgentPanel)
                    widget.log_activity(text)
                except:
                    pass
            self.call_from_thread(update_ui)

    def update_metrics(self, tokens: int, cost: float):
        def update_ui():
            self.query_one("#token-counter").update(f"Tokens: {tokens}")
            self.query_one("#cost-counter").update(f"Cost: ${cost:.4f}")
        self.call_from_thread(update_ui)

    def update_subagent_task(self, tool_id: str, input_data: dict, status: str):
        # Assign this tool_id to a slot if not exists.
        # If it doesn't exist, we must Create and Mount a new panel structure.
        
        need_create = False
        if tool_id not in self.subagent_map:
            need_create = True
            
        def safe_update_ui():
            if need_create:
                count = len(self.subagent_map) + 1
                new_id = f"sa_{tool_id}" # Widgets IDs should not contain funky chars, tool_id is usually safe but lets prefix
                self.subagent_map[tool_id] = new_id
                
                # Create the container box and the panel
                box = Static(classes="subagent-box", id=f"box_{new_id}")
                panel = SubAgentPanel(id=new_id)
                
                # Mount to container
                container = self.query_one("#subagents-container", VerticalScroll)
                container.mount(box)
                
                # Add content to box
                box.mount(Label(f"Sub-Agent {count}", classes="subagent-title"))
                box.mount(panel)
                
                # Scroll to ensure visible
                box.scroll_visible()
            
            # Now update the status content
            widget_id = self.subagent_map[tool_id]
            try:
                widget = self.query_one(f"#{widget_id}", SubAgentPanel)
                widget.update_status(f"[{status.upper()}]")
                desc = self.format_tool_input(input_data)
                widget.log_activity(f"[yellow]Task Definition:[/yellow]\n{desc}")
            except Exception as e:
                # If widget not found immediately (race condition?), log error to lead log
                self.query_one("#lead-log").write(f"[red]UI Sync Error: {e}[/]")

        self.call_from_thread(safe_update_ui)

    def complete_subagent_task(self, tool_id: str, result: any):
        if tool_id in self.subagent_map:
            slot_id = self.subagent_map[tool_id]
            def update_ui():
                try:
                    widget = self.query_one(f"#{slot_id}", SubAgentPanel)
                    widget.update_status("[DONE]")
                    formatted_result = self.format_tool_input(result) # Reuse json formatter
                    widget.log_activity(f"[green]Final Result:[/green]\n{formatted_result}")
                except:
                    pass
            
            self.call_from_thread(update_ui)

if __name__ == "__main__":
    app = ResearchDashboard()
    app.run()
