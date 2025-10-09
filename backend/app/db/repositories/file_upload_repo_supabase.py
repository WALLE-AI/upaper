from typing import Optional, List, Dict, Any
from datetime import datetime
from supabase import create_client, Client
import os

class SupabaseRepository:
    """Base repository providing helper methods for Supabase operations."""
    def __init__(self, table_name: str, supabase: Optional[Client] = None):
        if supabase:
            self.client = supabase
        else:
            self.client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
        self.table = self.client.table(table_name)

    def _check_error(self, res):
        if res.error:
            raise Exception(f"Supabase error: {res.error.message}")
        return res.data


class UploadFileRepo(SupabaseRepository):
    """Repository for the upload_files table"""
    def __init__(self, supabase: Optional[Client] = None):
        super().__init__("upload_files", supabase)

    # --- CRUD ---
    def create(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """插入一条文件记录"""
        record.setdefault("created_at", datetime.utcnow().isoformat())
        res = self.table.insert(record).execute()
        return self._check_error(res)[0]

    def get_by_id(self, file_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取文件"""
        res = self.table.select("*").eq("id", file_id).single().execute()
        data = self._check_error(res)
        return data if data else None

    def list_by_tenant(
        self,
        tenant_id: str,
        limit: int = 20,
        offset: int = 0,
        used: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """按租户查询文件，可选按 used 筛选"""
        query = self.table.select("*").eq("tenant_id", tenant_id)
        if used is not None:
            query = query.eq("used", used)
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        res = query.execute()
        return self._check_error(res)

    def mark_used(self, file_id: str, used_by: str) -> Dict[str, Any]:
        """标记文件为已使用"""
        update_data = {
            "used": True,
            "used_by": used_by,
            "used_at": datetime.utcnow().isoformat(),
        }
        res = self.table.update(update_data).eq("id", file_id).execute()
        return self._check_error(res)[0]

    def update(self, file_id: str, values: Dict[str, Any]) -> Dict[str, Any]:
        """更新文件字段"""
        res = self.table.update(values).eq("id", file_id).execute()
        return self._check_error(res)[0]

    def delete(self, file_id: str) -> bool:
        """删除文件"""
        res = self.table.delete().eq("id", file_id).execute()
        self._check_error(res)
        return True

    def get_by_hash(self, tenant_id: str, file_hash: str) -> Optional[Dict[str, Any]]:
        """按哈希值查重"""
        res = self.table.select("*").eq("tenant_id", tenant_id).eq("hash", file_hash).single().execute()
        data = self._check_error(res)
        return data if data else None
