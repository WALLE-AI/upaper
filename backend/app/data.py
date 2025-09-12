from __future__ import annotations
from typing import List, Dict
import random

from utils.get_hf_papers import get_hugging_face_top_daily_paper

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

hf_daily_data = [
    {
        "id": "2509.04664",
        "authors": [
            {
                "_id": "68be5810c123124955ef60ac",
                "name": "Adam Tauman Kalai",
                "hidden": False
            },
            {
                "_id": "68be5810c123124955ef60ad",
                "name": "Ofir Nachum",
                "hidden": False
            },
            {
                "_id": "68be5810c123124955ef60ae",
                "name": "Santosh S. Vempala",
                "hidden": False
            },
            {
                "_id": "68be5810c123124955ef60af",
                "name": "Edwin Zhang",
                "hidden": False
            }
        ],
        "publishedAt": "2025-09-04T21:26:31.000Z",
        "submittedOnDailyAt": "2025-09-08T02:44:20.973Z",
        "title": "Why Language Models Hallucinate",
        "submittedOnDailyBy": {
            "_id": "6039478ab3ecf716b1a5fd4d",
            "avatarUrl": "https://cdn-avatars.huggingface.co/v1/production/uploads/6039478ab3ecf716b1a5fd4d/_Thy4E7taiSYBLKxEKJbT.jpeg",
            "isPro": True,
            "fullname": "taesiri",
            "user": "taesiri",
            "type": "user"
        },
        "summary": "Like students facing hard exam questions, large language models sometimes\nguess when uncertain, producing plausible yet incorrect statements instead of\nadmitting uncertainty. Such \"hallucinations\" persist even in state-of-the-art\nsystems and undermine trust. We argue that language models hallucinate because\nthe training and evaluation procedures reward guessing over acknowledging\nuncertainty, and we analyze the statistical causes of hallucinations in the\nmodern training pipeline. Hallucinations need not be mysterious -- they\noriginate simply as errors in binary classification. If incorrect statements\ncannot be distinguished from facts, then hallucinations in pretrained language\nmodels will arise through natural statistical pressures. We then argue that\nhallucinations persist due to the way most evaluations are graded -- language\nmodels are optimized to be good test-takers, and guessing when uncertain\nimproves test performance. This \"epidemic\" of penalizing uncertain responses\ncan only be addressed through a socio-technical mitigation: modifying the\nscoring of existing benchmarks that are misaligned but dominate leaderboards,\nrather than introducing additional hallucination evaluations. This change may\nsteer the field toward more trustworthy AI systems.",
        "upvotes": 26,
        "discussionId": "68be5810c123124955ef60b0",
        "ai_summary": "Language models produce incorrect statements due to training and evaluation procedures that reward guessing over acknowledging uncertainty, leading to a need for socio-technical changes in benchmark scoring.",
        "ai_keywords": [
            "hallucinations",
            "binary classification",
            "uncertain responses",
            "trustworthy AI systems"
        ]
    }
]


from typing import List, Dict, Sequence, Mapping, Union, Optional

def hf_to_base_items(
    hf_daily_data: Sequence[Dict],
    *,
    ai_notes: Union[str, Sequence[str]] = (),
    default_badges: Sequence[str] = (),
    id_prefix: str = "p",
    start_index: int = 1,
    truncate_summary_to: Optional[int] = 180
) -> List[Dict]:
    """
    将 Hugging Face 每日数据（hf_daily_data）转换为 BASE_ITEMS 结构。

    参数:
        hf_daily_data: 原始列表（每个元素为 dict）
        ai_notes: 给所有条目统一附加的 aiNotes（字符串或字符串列表）
        default_badges: 给所有条目统一附加的 badges
        id_prefix: 生成 id 的前缀，例如 'p'
        start_index: 序号起始值，例如 1 -> p1, p2...
        truncate_summary_to: 摘要最大长度（None 表示不截断）

    返回:
        BASE_ITEMS: List[Dict]
    """
    # 简单的关键词 -> 规范标签映射（可按需扩充）
    tag_map = {
        "reinforcement learning": "Reinforcement-Learning",
        "reinforcement": "Reinforcement-Learning",
        "rl": "Reinforcement-Learning",
        "agent": "Agent",
        "agents": "Agent",
        "reasoning": "Reasoning",
        "plan": "Reasoning",
        "planning": "Reasoning",
        # 其它常见但不在你的目标标签中的关键词，默认归为 Other
        "hallucination": "Other",
        "hallucinations": "Other",
        "safety": "Other",
        "binary classification": "Other",
        "uncertainty": "Other",
        "trustworthy": "Other",
    }

    def pick_tags(item: Dict) -> List[str]:
        kws = [k.lower() for k in item.get("ai_keywords", []) if isinstance(k, str)]
        tags: List[str] = []
        for kw in kws:
            for key, tag in tag_map.items():
                if key in kw and tag not in tags:
                    tags.append(tag)
        return tags or ["Other"]

    # 统一处理 notes/badges
            # aiNotes 使用 ai_keywords
    badges_list = list(default_badges)

    base_items: List[Dict] = []
    for i, it in enumerate(hf_daily_data, start=start_index):
        title = it.get("title") or ""
        # 优先用 summary，其次 ai_summary
        summary = it.get("summary") or it.get("ai_summary") or ""
        # if truncate_summary_to and len(summary) > truncate_summary_to:
        #     summary = summary[: max(0, truncate_summary_to - 3)].rstrip() + "..."
        raw_keywords = it.get("ai_keywords") or []
        ai_notes = [str(k) for k in raw_keywords if isinstance(k, (str, int, float))]

        item_dict = {
            "id": f"{id_prefix}{i}",
            "title": title,
            "summary": summary,
            "source": "HF",
            "likes": int(it.get("upvotes") or 0),
            "comments": int(it.get("comments", 0) or 0),  # 源里通常没有评论数，默认 0
            "tags": pick_tags(it),
            "aiNotes": ai_notes,
            "badges":ai_notes,
        }
        base_items.append(item_dict)

    return base_items



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

def get_hf_daily_papers() -> List[Dict]:
    hf_daily_data = get_hugging_face_top_daily_paper()
    BASE_ITEMS = hf_to_base_items(
        hf_daily_data,
        ai_notes=["AT 解析(6个模型)"],                 # 可自定义
        default_badges=["Intern-S1", "GLM2.5", "Intern-S1-Image", "Intern-S1-Summary"],
        id_prefix="p",
        start_index=2,                                 # 让它对应示例里的 p2
        truncate_summary_to=120
    )
    return BASE_ITEMS

# # 生成更多样本，便于分页
# ALL_PAPERS: List[Dict] = []
# ALL_PAPERS.extend(BASE_ITEMS)
# for i in range(5, 10):  # 79 条
#     ALL_PAPERS.append(_random_item(i))
