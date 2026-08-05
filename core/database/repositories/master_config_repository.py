import json

from core.database.workspace_db import WorkspaceDB


class MasterConfigRepository:
    def __init__(self, workspace_db: WorkspaceDB):
        self.db = workspace_db

    def get(self) -> dict:
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM master_config WHERE id = 1").fetchone()
        result = dict(row)
        result["config_plc"] = json.loads(result["config_plc"])
        result["external_scanner"] = bool(result["external_scanner"])
        result.pop("id", None)
        return result

    def update(self, **values) -> dict:
        current = self.get()
        current.update({k: v for k, v in values.items() if v is not None})
        with self.db.connection() as conn:
            conn.execute("""UPDATE master_config SET master_img=?, config_plc=?, external_scanner=?, ok_piece=?, ng_piece=? WHERE id=1""",
                         (current["master_img"], json.dumps(current["config_plc"]), int(current["external_scanner"]), current["ok_piece"], current["ng_piece"]))
        return self.get()

    def reset_counters(self) -> dict:
        with self.db.connection() as conn:
            conn.execute("UPDATE master_config SET ok_piece=0, ng_piece=0 WHERE id=1")
        return self.get()
