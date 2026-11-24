## DynamoBench v0.1.1

### Highlights
- **Native Revit 2027 C# Ribbon Add-In (`addin_revit2027/`):** Added an `IExternalApplication` ribbon tab (`DynamoBench`) targeting .NET 10 (`net10.0-windows`) against Revit 2027 API (`v27.3.0.0`), allowing users to run verification exports directly inside Revit without opening Dynamo.
- **Four-Button Read–Write–Create Workflow:**
  - **Rooms (Read/Write):** Exports room IDs, numbers, names, levels, departments, enclosure status, and areas in `m²` (`revit2027_rooms_snapshot.json`).
  - **3D Sensors (Create):** Exports `DirectShape` sensor bounding boxes and dimensions converted from internal units to meters (`revit2027_sensors_snapshot.json`).
  - **Full Audit (All Tasks):** Exports both room and 3D sensor snapshots in a single run.
  - **Pre/Post Check:** Captures a pre-run baseline (`revit2027_baseline_snapshot.json`), compares post-run model state, flags silent anomalies (`DEPARTMENT_CHANGE_ON_UNENCLOSED_ROOM`, `WRONG_LEVEL_FILTER_OR_AREA_SHIFT`, `SENSOR_SCALE_ANOMALY_OVERSIZED`), and writes `revit2027_prepost_audit.json`.
- **Installer & Packaging (`Installer.iss`):** Added an Inno Setup script (`addin_revit2027/Installer.iss`) to install `DynamoBench.Revit2027.addin` and `DynamoBench.Revit2027.dll` into `%APPDATA%\Autodesk\Revit\Addins\2027` for Revit 2027 users.
