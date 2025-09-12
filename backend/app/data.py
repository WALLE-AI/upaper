from __future__ import annotations
from typing import List, Dict
import random

SOURCES = ["HF", "arXiv", "Cvpr2025", "Other"]
TAGS = [
    "AI-Infrastructure", "Agent", "Bench", "Image-Generation", "Multimodal",
    "Reinforcement-Learning", "Robot", "Video-Generation", "Other", "Reasoning"
]

BASE_ITEMS: List[Dict] = [
    {
        "id": "p1",
        "title": "Sharing is Caring: Efficient LM Post-Training with Collective RL Experience Sharing",
        "summary": "Post-training language models (LMs) with reinforcement learning (RL) can enhance complex reasoning without supervised fine-tuning...",
        "source": "HF",
        "likes": 194,
        "comments": 24,
        "tags": ["Reinforcement-Learning", "Agent", "Reasoning"],
        "aiNotes": ["AT 解析(6个模型)"],
        "badges": ["Intern-S1", "GLM4.5", "Intern-S1-Image", "Intern-S1-Summary"]
    },
    {
        "id": "p2",
        "title": "Why Language Models Hallucinate",
        "summary": "Large language models sometimes guess when uncertain, producing plausible yet incorrect statements...",
        "source": "HF",
        "likes": 145,
        "comments": 7,
        "tags": ["Other"],
        "aiNotes": ["AT 解析(6个模型)"],
        "badges": ["Intern-S1", "GLM2.5", "Intern-S1-Image", "Intern-S1-Summary"]
    },
    {
        "id": "p3",
        "title": "Reverse-Engineered Reasoning for Open-Ended Generation",
        "summary": "The 'deep reasoning' paradigm has spurred advances in math; however, open-ended creative generation remains challenging...",
        "source": "HF",
        "likes": 128,
        "comments": 4,
        "tags": ["Agent", "Reasoning"],
        "aiNotes": ["AT 解析(6个模型)"],
        "badges": ["Intern-S1", "GLM4.5", "Intern-S1-Image", "Intern-S1-Summary"]
    },
    {
        "id": "p4",
        "title": "Parallel-R1: Towards Parallel Thinking via Reinforcement Learning",
        "summary": "Parallel thinking enhances reasoning capabilities via multiple concurrent reasoning paths...",
        "source": "HF",
        "likes": 72,
        "comments": 3,
        "tags": ["Reinforcement-Learning"],
        "aiNotes": ["AT 解析(4个模型)"],
        "badges": ["Intern-S1", "GLM4.5", "Intern-S1-Tags", "pdf2md"]
    }
]

def _random_item(i: int) -> dict:
    rnd = random.Random(2024 + i)
    base = rnd.choice(BASE_ITEMS).copy()
    base["id"] = f"p{i}"
    base["title"] = base["title"] + f" (Sample #{i})"
    base["likes"] = rnd.randint(10, 500)
    base["comments"] = rnd.randint(0, 40)
    base["source"] = rnd.choice(SOURCES)
    base["tags"] = rnd.sample(TAGS, k=rnd.randint(1, 3))
    return base

# 生成更多样本，便于分页
ALL_PAPERS: List[Dict] = []
ALL_PAPERS.extend(BASE_ITEMS)
for i in range(5, 80):  # 79 条
    ALL_PAPERS.append(_random_item(i))
