# UiPath Multi-Agent Automation Builder

An intelligent multi-agent system that automates the creation of UiPath RPA workflows from natural language process descriptions. Built with LangGraph and Pydantic for robust agent orchestration.

## Features

- **LLM-First Reasoning**: Each stage prioritizes model-based reasoning and uses deterministic logic as fallback
- **Intelligent Requirements Analysis**: Extracts entities, identifies patterns, and generates comprehensive requirements
- **Automated Solution Design**: Creates To-Be process flowcharts and architectural decisions
- **UiPath Workflow Generation**: Builds XAML files and project structures
- **Quality Assurance**: Multi-dimensional code and process reviews
- **Interactive Workflow**: Human-in-the-loop approvals at key stages
- **Context Packet Handover**: Rich reasoning context is packaged and passed stage-to-stage
- **Extensible Architecture**: Modular agents with configurable prompts

## Architecture

The system uses a sequential agent pipeline:
1. **Requirements Agent**: Analyzes process descriptions and extracts requirements
2. **Design Agent**: Creates solution architecture and flowcharts
3. **Build Agent**: Generates UiPath XAML workflows and project files
4. **Documentation Agent**: Produces comprehensive documentation
5. **Quality Agent**: Performs final reviews and assessments

## Installation

```bash
# Clone the repository
git clone https://github.com/dag2932/uipath-multi-agent-system.git
cd uipath-multi-agent-system

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Interactive Mode
```bash
python main.py
```
Follow the prompts to describe your business process.

### Batch Mode
```bash
echo "Your process description here" | python main.py
```

### Example Process Description
```
Daily check contracts in SAP SuccessFactors, send email reminders for contracts expiring in 30 days.
- Check at 6 AM daily
- Identify employees with expiring contracts
- Send personalized email notifications
- Log all actions for audit
```

## Outputs

The system generates:
- `01_requirements.md`: Detailed requirements analysis
- `02_solution_design.md`: Solution design with flowcharts
- `03_build_notes.md`: Build instructions
- `04_documentation.md`: Complete documentation
- `05_code_quality_review.md`: Quality assessment
- `uipath_project/`: UiPath project files including XAML workflows

## Configuration

- Set `LLM_MODEL` environment variable to change the AI model (default: gpt-4o-mini)
- Set `OPENAI_API_KEY` for LLM-first execution
- `LLM_FIRST=true|false` (default: `true`) to prioritize model reasoning
- `LLM_REQUIRED=true|false` (default: `false`) to fail fast when LLM is unavailable

## Requirements

- Python 3.9+
- OpenAI API key (recommended for LLM-first mode)
- UiPath Studio (for running generated workflows)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details.