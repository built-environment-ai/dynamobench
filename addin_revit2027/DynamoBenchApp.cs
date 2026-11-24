using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.Json;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Architecture;
using Autodesk.Revit.UI;

namespace DynamoBench.Revit2027
{
    public class DynamoBenchApp : IExternalApplication
    {
        public Result OnStartup(UIControlledApplication app)
        {
            const string tabName = "DynamoBench";
            try { app.CreateRibbonTab(tabName); } catch { }
            RibbonPanel panel = app.CreateRibbonPanel(tabName, "Read-Write-Create Verifier");
            string dllPath = Assembly.GetExecutingAssembly().Location;

            panel.AddItem(new PushButtonData(
                "CaptureRooms",
                "Rooms\n(Read/Write)",
                dllPath,
                "DynamoBench.Revit2027.CaptureRoomsCommand"
            )
            {
                ToolTip = "Export room area (m2), enclosure state, level, and department for Read/Write checks."
            });

            panel.AddItem(new PushButtonData(
                "CaptureSensors",
                "3D Sensors\n(Create)",
                dllPath,
                "DynamoBench.Revit2027.CaptureSensorsCommand"
            )
            {
                ToolTip = "Export DirectShape sensor bounding boxes and centroids in meters for Create checks."
            });

            panel.AddItem(new PushButtonData(
                "RunFullAudit",
                "Full Audit\n(All Tasks)",
                dllPath,
                "DynamoBench.Revit2027.RunFullAuditCommand"
            )
            {
                ToolTip = "Export both Room and 3D DirectShape sensor snapshots in one click."
            });

            panel.AddItem(new PushButtonData(
                "PrePostCheck",
                "Pre/Post\nCheck",
                dllPath,
                "DynamoBench.Revit2027.PrePostCheckCommand"
            )
            {
                ToolTip = "First click saves a baseline before running Dynamo; second click compares state and flags silent failures."
            });

            return Result.Succeeded;
        }

        public Result OnShutdown(UIControlledApplication app) => Result.Succeeded;
    }

    internal sealed class RoomSnapshotRecord
    {
        public long id { get; set; }
        public string number { get; set; } = "";
        public string name { get; set; } = "";
        public string level { get; set; } = "";
        public string department { get; set; } = "";
        public double area_m2 { get; set; }
        public bool is_enclosed { get; set; }
    }

    internal sealed class SensorSnapshotRecord
    {
        public long id { get; set; }
        public string name { get; set; } = "";
        public string category { get; set; } = "";
        public double[] min_m { get; set; } = Array.Empty<double>();
        public double[] max_m { get; set; } = Array.Empty<double>();
        public double[] size_m { get; set; } = Array.Empty<double>();
    }

    internal sealed class AuditFinding
    {
        public string code { get; set; } = "";
        public string detail { get; set; } = "";
    }

    internal sealed class ModelSnapshot
    {
        public string model { get; set; } = "";
        public string captured_utc { get; set; } = "";
        public List<RoomSnapshotRecord> rooms { get; set; } = new();
        public List<SensorSnapshotRecord> sensors { get; set; } = new();
    }

    internal static class BenchmarkSnapshotExporter
    {
        public static string ReportsDir =>
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "dynamobench_v1", "reports");

        public static List<RoomSnapshotRecord> CollectRooms(Document doc)
        {
            return new FilteredElementCollector(doc)
                .OfCategory(BuiltInCategory.OST_Rooms)
                .WhereElementIsNotElementType()
                .Cast<Room>()
                .Select(r => new RoomSnapshotRecord
                {
                    id = r.Id.Value,
                    number = r.get_Parameter(BuiltInParameter.ROOM_NUMBER)?.AsString() ?? "",
                    name = r.get_Parameter(BuiltInParameter.ROOM_NAME)?.AsString() ?? "",
                    level = r.Level?.Name ?? "",
                    department = r.get_Parameter(BuiltInParameter.ROOM_DEPARTMENT)?.AsString() ?? "",
                    area_m2 = Math.Round(UnitUtils.ConvertFromInternalUnits(r.Area, UnitTypeId.SquareMeters), 4),
                    is_enclosed = r.Area > 0.0
                })
                .OrderBy(x => x.number)
                .ToList();
        }

        public static List<SensorSnapshotRecord> CollectSensors(Document doc)
        {
            return new FilteredElementCollector(doc)
                .OfClass(typeof(DirectShape))
                .WhereElementIsNotElementType()
                .Cast<DirectShape>()
                .Select(ds =>
                {
                    BoundingBoxXYZ? bb = ds.get_BoundingBox(null);
                    double minX = bb != null ? UnitUtils.ConvertFromInternalUnits(bb.Min.X, UnitTypeId.Meters) : 0.0;
                    double minY = bb != null ? UnitUtils.ConvertFromInternalUnits(bb.Min.Y, UnitTypeId.Meters) : 0.0;
                    double minZ = bb != null ? UnitUtils.ConvertFromInternalUnits(bb.Min.Z, UnitTypeId.Meters) : 0.0;
                    double maxX = bb != null ? UnitUtils.ConvertFromInternalUnits(bb.Max.X, UnitTypeId.Meters) : 0.0;
                    double maxY = bb != null ? UnitUtils.ConvertFromInternalUnits(bb.Max.Y, UnitTypeId.Meters) : 0.0;
                    double maxZ = bb != null ? UnitUtils.ConvertFromInternalUnits(bb.Max.Z, UnitTypeId.Meters) : 0.0;

                    return new SensorSnapshotRecord
                    {
                        id = ds.Id.Value,
                        name = ds.Name ?? "",
                        category = ds.Category?.Name ?? "",
                        min_m = new[] { Math.Round(minX, 4), Math.Round(minY, 4), Math.Round(minZ, 4) },
                        max_m = new[] { Math.Round(maxX, 4), Math.Round(maxY, 4), Math.Round(maxZ, 4) },
                        size_m = new[] { Math.Round(maxX - minX, 4), Math.Round(maxY - minY, 4), Math.Round(maxZ - minZ, 4) }
                    };
                })
                .OrderBy(x => x.id)
                .ToList();
        }

        public static ModelSnapshot CaptureSnapshot(Document doc)
        {
            return new ModelSnapshot
            {
                model = doc.Title,
                captured_utc = DateTime.UtcNow.ToString("o"),
                rooms = CollectRooms(doc),
                sensors = CollectSensors(doc)
            };
        }

        public static string ExportRooms(Document doc)
        {
            var rooms = CollectRooms(doc);
            Directory.CreateDirectory(ReportsDir);
            string outPath = Path.Combine(ReportsDir, "revit2027_rooms_snapshot.json");
            File.WriteAllText(outPath, JsonSerializer.Serialize(new
            {
                model = doc.Title,
                captured_utc = DateTime.UtcNow.ToString("o"),
                room_count = rooms.Count,
                records = rooms
            }, new JsonSerializerOptions { WriteIndented = true }));
            return outPath;
        }

        public static string ExportSensors(Document doc)
        {
            var sensors = CollectSensors(doc);
            Directory.CreateDirectory(ReportsDir);
            string outPath = Path.Combine(ReportsDir, "revit2027_sensors_snapshot.json");
            File.WriteAllText(outPath, JsonSerializer.Serialize(new
            {
                model = doc.Title,
                captured_utc = DateTime.UtcNow.ToString("o"),
                sensor_count = sensors.Count,
                records = sensors
            }, new JsonSerializerOptions { WriteIndented = true }));
            return outPath;
        }
    }

    [Transaction(TransactionMode.ReadOnly)]
    public class CaptureRoomsCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            Document doc = commandData.Application.ActiveUIDocument.Document;
            string outPath = BenchmarkSnapshotExporter.ExportRooms(doc);
            TaskDialog.Show("DynamoBench v0.1 — Rooms", $"Exported room state to:\n{outPath}");
            return Result.Succeeded;
        }
    }

    [Transaction(TransactionMode.ReadOnly)]
    public class CaptureSensorsCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            Document doc = commandData.Application.ActiveUIDocument.Document;
            string outPath = BenchmarkSnapshotExporter.ExportSensors(doc);
            TaskDialog.Show("DynamoBench v0.1 — 3D Sensors", $"Exported DirectShape sensor state (meters) to:\n{outPath}");
            return Result.Succeeded;
        }
    }

    [Transaction(TransactionMode.ReadOnly)]
    public class RunFullAuditCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            Document doc = commandData.Application.ActiveUIDocument.Document;
            string roomsPath = BenchmarkSnapshotExporter.ExportRooms(doc);
            string sensorsPath = BenchmarkSnapshotExporter.ExportSensors(doc);
            TaskDialog.Show("DynamoBench v0.1 — Full Audit", $"Exported:\n1. {roomsPath}\n2. {sensorsPath}");
            return Result.Succeeded;
        }
    }

    [Transaction(TransactionMode.ReadOnly)]
    public class PrePostCheckCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            Document doc = commandData.Application.ActiveUIDocument.Document;
            Directory.CreateDirectory(BenchmarkSnapshotExporter.ReportsDir);
            string baselinePath = Path.Combine(BenchmarkSnapshotExporter.ReportsDir, "revit2027_baseline_snapshot.json");
            string auditPath = Path.Combine(BenchmarkSnapshotExporter.ReportsDir, "revit2027_prepost_audit.json");

            if (!File.Exists(baselinePath))
            {
                ModelSnapshot baseline = BenchmarkSnapshotExporter.CaptureSnapshot(doc);
                File.WriteAllText(baselinePath, JsonSerializer.Serialize(baseline, new JsonSerializerOptions { WriteIndented = true }));
                TaskDialog.Show(
                    "DynamoBench Pre/Post Check — Baseline Saved",
                    $"Saved pre-run baseline ({baseline.rooms.Count} rooms, {baseline.sensors.Count} DirectShape elements) to:\n{baselinePath}\n\nRun your Dynamo script, then click Pre/Post Check again to compare."
                );
                return Result.Succeeded;
            }

            ModelSnapshot? before = JsonSerializer.Deserialize<ModelSnapshot>(File.ReadAllText(baselinePath));
            ModelSnapshot after = BenchmarkSnapshotExporter.CaptureSnapshot(doc);
            var findings = new List<AuditFinding>();

            if (before != null)
            {
                var beforeRooms = before.rooms.ToDictionary(r => r.id);
                foreach (var rAfter in after.rooms)
                {
                    if (!beforeRooms.TryGetValue(rAfter.id, out var rBefore)) continue;

                    if (!rBefore.is_enclosed && rAfter.department != rBefore.department && !string.IsNullOrWhiteSpace(rAfter.department))
                    {
                        findings.Add(new AuditFinding { code = "DEPARTMENT_CHANGE_ON_UNENCLOSED_ROOM", detail = $"Unenclosed room mutated ROOM_DEPARTMENT from '{rBefore.department }' to '{rAfter.department}'."
                        });
                    }

                    if (Math.Abs(rAfter.area_m2 - rBefore.area_m2) > 0.01 && rAfter.level != rBefore.level)
                    {
                        findings.Add(new AuditFinding { code = "WRONG_LEVEL_FILTER_OR_AREA_SHIFT", detail = $"Room area shifted ({rBefore.area_m2 } -> {rAfter.area_m2} m2) with level '{rBefore.level}' -> '{rAfter.level}'."
                        });
                    }
                }

                var beforeSensorIds = before.sensors.Select(s => s.id).ToHashSet();
                foreach (var sAfter in after.sensors.Where(s => !beforeSensorIds.Contains(s.id)))
                {
                    double maxDim = sAfter.size_m.Length > 0 ? sAfter.size_m.Max() : 0.0;
                    if (maxDim > 1.0)
                    {
                        findings.Add(new AuditFinding { code = "SENSOR_SCALE_ANOMALY_OVERSIZED", detail = $"New DirectShape bounding box max dimension is {maxDim:F4} m (check if feet/mm were passed as meters)."
                        });
                    }
                }
            }

            var report = new
            {
                model = doc.Title,
                compared_utc = DateTime.UtcNow.ToString("o"),
                baseline_rooms = before?.rooms.Count ?? 0,
                current_rooms = after.rooms.Count,
                baseline_sensors = before?.sensors.Count ?? 0,
                current_sensors = after.sensors.Count,
                silent_findings_count = findings.Count,
                findings
            };
            File.WriteAllText(auditPath, JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
            File.Delete(baselinePath);

            string summary = findings.Count == 0
                ? $"No silent anomalies flagged ({after.rooms.Count} rooms, {after.sensors.Count} sensors)."
                : string.Join("\n", findings.Take(5).Select(f => $"[{f.code}] {f.detail}"));

            TaskDialog.Show("DynamoBench Pre/Post Check — Result", $"Findings: {findings.Count}\nReport: {auditPath}\n\n{summary}");
            return Result.Succeeded;
        }
    }
}
