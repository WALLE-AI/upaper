export type Paper = {
  id: string;
  title: string;
  summary: string;
  source: "HF" | "arXiv" | "Cvpr2025" | "Other" | string;
  likes: number;
  comments: number;
  tags: string[];
  aiNotes?: string[];
  badges?: string[];
};
export type PaperQuery = {
  search?: string;
  sources?: string[];
  tags?: string[];
  page?: number;
  pageSize?: number;
};
export type PaperListResp = {
  items: Paper[];
  total: number;
};
