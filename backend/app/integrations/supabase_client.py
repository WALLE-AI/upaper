"""Supabase client initialization as a Flask extension."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from flask import Flask
from supabase import Client, create_client


@dataclass
class _SBClients:
    anon: Optional[Client] = None
    service: Optional[Client] = None


class SupabaseExt:
    def __init__(self) -> None:
        self.clients = _SBClients()

    def init_app(self, app: Flask) -> None:
        url = app.config.get("SUPABASE_URL")
        anon_key = app.config.get("SUPABASE_ANON_KEY")
        service_key = app.config.get("SUPABASE_SERVICE_ROLE_KEY")
        if url and anon_key:
            self.clients.anon = create_client(url, anon_key)
        if url and service_key:
            self.clients.service = create_client(url, service_key)

    @property
    def anon(self) -> Optional[Client]:
        return self.clients.anon

    @property
    def service(self) -> Optional[Client]:
        return self.clients.service


supabase_ext = SupabaseExt()
