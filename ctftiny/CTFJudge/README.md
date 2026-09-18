# CTFJudge: LLM as a Judge for Offensive Security Agents
This is the official repository for CTFJudge from "Towards Effective Offensive Security LLM Agents: Hyperparameter Tuning, LLM as a Judge, and a Lightweight CTF Benchmark" (AAAI'26) [[paper](https://arxiv.org/abs/2508.05674)].

For CTFTiny benchmark, please refer to [CTFTiny Official Repository](https://github.com/NYU-LLM-CTF/CTFTiny/tree/main).

## Overview
This system uses three LLM-powered agents to:

1.**Agent 1**: Decompose writeups into structured solution steps

2.**Agent 2**: Extract and summarize trajectory actions from JSON logs

3.**Agent 3**: Perform qualitative comparison and scoring between writeup and trajectory


## Prerequisites

- Python 3.8+
- Anthropic API key


```bash
export ANTHROPIC_API_KEY='your-api-key'
```

## Usage

```bash
# Run evaluation on all challenge pairs
python run_evaluation.py --writeups-dir <path> --trajs-dir <path>

# Run evaluation on a specific challenge
python run_evaluation.py --challenge <challenge_name> --writeups-dir <path> --trajs-dir <path>
```

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--challenge`, `-c` | None | Evaluate a specific challenge by name (without extension) |
| `--writeups-dir` | `writeups` | Directory containing `.txt` writeup files |
| `--trajs-dir` | `trajs` | Directory containing `.json` trajectory files |
| `--outputs-dir` | `outputs` | Directory for intermediate agent outputs |
| `--evaluations-dir` | `evaluations` | Directory for final evaluation reports |
| `--errors-dir` | `errors` | Directory for error logs |

## Notes

- Challenge names should match the full docker container names (e.g., `2023q-web-smug_dino`)
- Writeup and trajectory files must share the same base name (`<name>.txt` ↔ `<name>.json`)
- Modify the config file to adjust model selection and token limits (applies to all 3 agents)
- Modifications may be required if using a different trajectory format other than [nyuctf_agents](https://github.com/NYU-LLM-CTF/nyuctf_agents) format.
