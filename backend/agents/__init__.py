# Agents package
# Agent 1: 数据采集 (api/inspection.py — REST API, 不使用 LangGraph)
# Agent 2: 智能评分 (agents/scoring/ — LangGraph, Qwen-plus)
# Agent 3: 总结分析 (agents/report/ — LangGraph, DeepSeek)
# Agent 4: 整改审核 (agents/rectification/ — Qwen-VL, checker.py)
# Orchestrator: 全自动编排 (agents/orchestrator/ — Agent2 → Agent3 → Agent4)

