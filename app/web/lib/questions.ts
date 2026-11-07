// Questions the dashboard sends to the chat when something is clicked. They carry the current
// filters, so the answer matches what's on screen.

import { fullDay } from "./format";
import type { Filters, MachineType } from "./types";

const PLURAL: Record<MachineType, string> = {
  Forklift: "forklifts",
  "Reach Truck": "reach trucks",
  PPT: "PPTs",
};

const when = (filters: Filters) => (filters.day ? `on ${fullDay(filters.day)}` : "this week");
const atBranch = (filters: Filters) => (filters.branch ? ` at ${filters.branch}` : "");
const machines = (filters: Filters) => (filters.type ? PLURAL[filters.type] : "machines");
const onType = (filters: Filters) => (filters.type ? ` on ${PLURAL[filters.type]}` : "");

export const kpiQuestions = (filters: Filters) => ({
  runHours: `Which ${machines(filters)} ran the most hours${atBranch(filters)} ${when(filters)}?`,
  active: `Which ${machines(filters)} didn't run${atBranch(filters)} ${when(filters)}?`,
  impacts: `Which drivers had the most impacts${onType(filters)}${atBranch(filters)} ${when(filters)}?`,
  harsh: `Which drivers had the most harsh events${onType(filters)}${atBranch(filters)} ${when(filters)}?`,
});

export const driverQuestion = (name: string, filters: Filters) =>
  `Break down ${name}'s events by type${onType(filters)}${atBranch(filters)} ${when(filters)}.`;

export const machineQuestion = (refNo: string, filters: Filters) =>
  filters.day
    ? `How many hours did ${refNo} run ${when(filters)}, and what events did it have?`
    : `How many hours did ${refNo} run each day this week?`;
