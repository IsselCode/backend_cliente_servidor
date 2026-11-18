"""Metadatos de los frames JPEG de vista previa enviados por WebSocket."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from core.contracts.camera import EncodedFrame


class FrameMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["frame"] = "frame"
    frame_id: str
    width: int
    height: int
    captured_at: datetime
    encoding: Literal["jpeg"] = "jpeg"
    purpose: Literal["preview"] = "preview"

    @classmethod
    def from_frame(cls, frame: EncodedFrame) -> "FrameMessage":
        return cls(
            frame_id=frame.frame_id, width=frame.width, height=frame.height,
            captured_at=frame.captured_at,
        )
