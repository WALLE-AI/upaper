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
    notes_list = [ai_notes] if isinstance(ai_notes, str) else list(ai_notes)
    badges_list = list(default_badges)

    base_items: List[Dict] = []
    for i, it in enumerate(hf_daily_data, start=start_index):
        title = it.get("title") or ""
        # 优先用 summary，其次 ai_summary
        summary = it.get("summary") or it.get("ai_summary") or ""
        if truncate_summary_to and len(summary) > truncate_summary_to:
            summary = summary[: max(0, truncate_summary_to - 3)].rstrip() + "..."

        item_dict = {
            "id": f"{id_prefix}{i}",
            "title": title,
            "summary": summary,
            "source": "HF",
            "likes": int(it.get("upvotes") or 0),
            "comments": int(it.get("comments", 0) or 0),  # 源里通常没有评论数，默认 0
            "tags": pick_tags(it),
            "aiNotes": notes_list[:] if notes_list else [],
            "badges": badges_list[:],
        }
        base_items.append(item_dict)

    return base_items


# --- 示例用法 ---
if __name__ == "__main__":
    hf_daily_data = [
        {
            "id": "2509.04664",
            "authors": [
                {"_id": "68be...", "name": "Adam Tauman Kalai", "hidden": False},
                {"_id": "68be...", "name": "Ofir Nachum", "hidden": False},
            ],
            "publishedAt": "2025-09-04T21:26:31.000Z",
            "submittedOnDailyAt": "2025-09-08T02:44:20.973Z",
            "title": "Why Language Models Hallucinate",
            "submittedOnDailyBy": {"user": "taesiri"},
            "summary": "Like students facing hard exam questions, large language models sometimes guess...",
            "upvotes": 26,
            "discussionId": "68be5810c123124955ef60b0",
            "ai_summary": "Language models produce incorrect statements due to training and evaluation...",
            "ai_keywords": [
                "hallucinations",
                "binary classification",
                "uncertain responses",
                "trustworthy AI systems",
            ],
        }
    ]

    BASE_ITEMS = hf_to_base_items(
        hf_daily_data,
        ai_notes=["AT 解析(6个模型)"],                 # 可自定义
        default_badges=["Intern-S1", "GLM2.5", "Intern-S1-Image", "Intern-S1-Summary"],
        id_prefix="p",
        start_index=2,                                 # 让它对应示例里的 p2
        truncate_summary_to=120
    )
    print(BASE_ITEMS)