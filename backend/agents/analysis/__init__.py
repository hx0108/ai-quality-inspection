"""
Agent 4: 综合分析 Agent (Analysis Agent)

基于已有的评分和报告数据，通过 DeepSeek-V3.2 大模型进行多维度智能对比分析。
支持三种模式：跨项目对比 / 跨时段对比 / 全项目概览

数据流向：Report(content_json) → Analysis(读取对比) → 管理层决策
"""
from agents.analysis.graph import build_analysis_graph

__all__ = ["build_analysis_graph"]
