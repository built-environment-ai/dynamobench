# -*- coding: utf-8 -*-
"""
DynamoBench Independent Revit API Room State Extractor (Revit 2027 / PythonNet3)
Extracts ALL rooms in the active Revit document directly via Autodesk.Revit.DB
without task-specific filtering or Dynamo room wrapper nodes.
"""
import clr
import hashlib
import json
import os
from datetime import datetime, timezone

clr.AddReference("RevitAPI")
clr.AddReference("RevitServices")

from Autodesk.Revit.DB import (
    BuiltInCategory,
    BuiltInParameter,
    FilteredElementCollector,
    UnitTypeId,
    UnitUtils,
)
from RevitServices.Persistence import DocumentManager

doc = DocumentManager.Instance.CurrentDBDocument
app = doc.Application

default_out = r"C:\Users\e-hbe\dynamobench_v1\reports\revit_room_state.json"
output_path = IN[0] if (len(IN) > 0 and IN[0]) else default_out


def compute_file_sha256(filepath):
    if not filepath or not os.path.isfile(filepath):
        return "UNSAVED_OR_CLOUD_MODEL"
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def get_param_str(elem, bip):
    p = elem.get_Parameter(bip)
    if p is None or not p.HasValue:
        return ""
    val = p.AsString()
    return val.strip() if val is not None else ""


collector = (
    FilteredElementCollector(doc)
    .OfCategory(BuiltInCategory.OST_Rooms)
    .WhereElementIsNotElementType()
)

rooms_data = []
for room in collector:
    area_param = room.get_Parameter(BuiltInParameter.ROOM_AREA)
    raw_area_sqft = area_param.AsDouble() if (area_param and area_param.HasValue) else 0.0
    area_m2 = round(UnitUtils.ConvertFromInternalUnits(raw_area_sqft, UnitTypeId.SquareMeters), 6)

    level_name = ""
    if room.Level is not None:
        level_name = room.Level.Name.strip()

    rooms_data.append({
        "unique_id": room.UniqueId,
        "element_id": int(room.Id.Value),
        "number": get_param_str(room, BuiltInParameter.ROOM_NUMBER),
        "name": get_param_str(room, BuiltInParameter.ROOM_NAME),
        "level": level_name,
        "area_sqft_internal": round(raw_area_sqft, 6),
        "area_m2": area_m2,
        "is_placed": room.Location is not None,
        "is_enclosed": raw_area_sqft > 0.0,
    })

rooms_data.sort(key=lambda r: (r["level"], r["number"], r["unique_id"]))

model_path = doc.PathName
snapshot = {
    "schema_version": "0.1.0",
    "extracted_at_utc": datetime.now(timezone.utc).isoformat(),
    "environment": {
        "revit_version": str(app.VersionNumber),
        "revit_build": str(app.VersionBuild),
        "revit_locale": str(app.Language),
        "model_title": str(doc.Title),
        "model_path": str(model_path),
        "model_sha256": compute_file_sha256(model_path),
    },
    "total_room_count": len(rooms_data),
    "rooms": rooms_data,
}

os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(snapshot, f, indent=2, ensure_ascii=False)

OUT = f"Extracted {len(rooms_data)} rooms to {output_path}"
