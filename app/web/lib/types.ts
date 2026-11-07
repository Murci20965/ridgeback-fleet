// Mirrors app/api/schemas.py. The API publishes the full contract at /api/v1/docs.

export type MachineType = "Forklift" | "Reach Truck" | "PPT";
export type Branch = "Airport" | "Harbour" | "Northgate" | "Riverside";

export const MACHINE_TYPES: MachineType[] = ["Forklift", "Reach Truck", "PPT"];
export const BRANCHES: Branch[] = ["Airport", "Harbour", "Northgate", "Riverside"];

export interface Coverage {
  first_date: string;
  last_date: string;
  days_with_data: number;
  week_start: string;
  week_end: string;
}

export interface Kpis {
  run_hours: number;
  active_machines: number;
  fleet_size: number;
  impacts: number;
  harsh_events: number;
  idle_events: number;
  unattributed_impacts: number;
}

export interface AttentionItem {
  severity: "critical" | "warning";
  kind: string;
  title: string;
  detail: string;
  question: string;
}

export interface MachineRow {
  ref_no: string;
  machine_type: MachineType;
  assigned_branch: string;
  reported_branches: string[];
  run_hours: number;
  active: boolean;
}

export interface DriverRow {
  driver_name: string | null;
  impacts: number;
  harsh: number;
  idle: number;
  safety_total: number;
}

export interface BranchRow {
  branch: Branch;
  run_hours: number;
  active_machines: number;
  impacts: number;
  harsh: number;
}

export interface DailySummary {
  event_date: string;
  run_hours: number;
  active_machines: number;
  impacts: number;
  harsh_events: number;
}

export interface DailyBranchHours {
  event_date: string;
  branch: Branch;
  run_hours: number;
}

export interface PipelineStatus {
  last_run_at: string;
  files: number;
  files_failed: number;
  files_partial: number;
  rows_total: number;
  rows_loaded: number;
  rows_rejected: number;
  rows_duplicate: number;
}

export interface Dashboard {
  coverage: Coverage | null;
  from_date: string | null;
  to_date: string | null;
  headline: string | null;
  kpis: Kpis | null;
  attention: AttentionItem[];
  machines: MachineRow[];
  drivers: DriverRow[];
  branches: BranchRow[];
  daily: DailySummary[];
  daily_branch_hours: DailyBranchHours[];
  pipeline: PipelineStatus | null;
}

export interface Filters {
  day: string | null;
  branch: Branch | null;
  type: MachineType | null;
}

export interface TraceStep {
  tool: string;
  arguments: Record<string, unknown> | null;
  rows: number | null;
  error: string | null;
}

export type ChatEvent =
  | { type: "status"; text: string }
  | { type: "answer"; text: string; verified: boolean; trace: TraceStep[]; model: string | null }
  | { type: "error"; message: string };
