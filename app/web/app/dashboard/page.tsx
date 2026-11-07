import { redirect } from "next/navigation";
import { AttentionList } from "@/components/AttentionList";
import { BranchActivity } from "@/components/BranchActivity";
import { Chat } from "@/components/Chat";
import { ChatBridge } from "@/components/ChatBridge";
import { DriverTable } from "@/components/DriverTable";
import { FilterBar } from "@/components/FilterBar";
import { FilterProvider, PendingFrame } from "@/components/FilterProvider";
import { Header } from "@/components/Header";
import { Headline } from "@/components/Headline";
import { KpiRow } from "@/components/KpiRow";
import { MachineHours } from "@/components/MachineHours";
import { PipelineFooter } from "@/components/PipelineFooter";
import { DayOutsideData, fetchDashboard } from "@/lib/api";
import { BRANCHES, MACHINE_TYPES, type Branch, type Filters, type MachineType } from "@/lib/types";

type SearchParams = Record<string, string | string[] | undefined>;

function readFilters(params: SearchParams): Filters {
  const day = typeof params.day === "string" && /^\d{4}-\d{2}-\d{2}$/.test(params.day);
  return {
    day: day ? (params.day as string) : null,
    branch: BRANCHES.includes(params.branch as Branch) ? (params.branch as Branch) : null,
    type: MACHINE_TYPES.includes(params.type as MachineType) ? (params.type as MachineType) : null,
  };
}

async function load(filters: Filters) {
  try {
    return await fetchDashboard(filters);
  } catch (error) {
    if (error instanceof DayOutsideData) redirect("/dashboard");
    throw error;
  }
}

export default async function Page({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const filters = readFilters(await searchParams);
  const data = await load(filters);

  return (
    <FilterProvider filters={filters}>
        <ChatBridge>
        <div className="flex min-h-dvh flex-col lg:h-dvh">
          <Header pipeline={data.pipeline} current="dashboard" />
          <div className="app-layout mx-auto grid min-h-0 w-full max-w-[1480px] flex-1 gap-5 px-4 pb-4 lg:grid-cols-[minmax(0,1fr)_380px] lg:grid-rows-[minmax(0,1fr)] lg:gap-6 lg:px-6 lg:pt-4 lg:pb-6">
            <main className="min-w-0 pb-20 lg:overflow-y-auto lg:pb-0 lg:pr-1">
              {data.coverage && data.kpis ? (
                <>
                  <PendingFrame>
                    <Headline
                      filters={filters}
                      from={data.from_date!}
                      to={data.to_date!}
                      text={data.headline ?? ""}
                    />
                  </PendingFrame>
                  <FilterBar coverage={data.coverage} />
                  <PendingFrame>
                    <KpiRow kpis={data.kpis} />
                    <div className="rise mt-5 grid gap-5 xl:grid-cols-2">
                      <AttentionList items={data.attention} />
                      <DriverTable drivers={data.drivers} />
                      <MachineHours machines={data.machines} isDay={Boolean(filters.day)} />
                      <BranchActivity
                        coverage={data.coverage}
                        daily={data.daily_branch_hours}
                        branches={data.branches}
                      />
                    </div>
                    <PipelineFooter pipeline={data.pipeline} />
                  </PendingFrame>
                </>
              ) : (
                <div className="mt-6 rounded-xl border border-line bg-surface p-8 text-center">
                  <h2 className="font-medium">No fleet data yet</h2>
                  <p className="mt-1 text-sm text-ink-2">
                    Figures appear here after the pipeline loads its first file.
                  </p>
                </div>
              )}
            </main>
            <Chat coverage={data.coverage} />
        </div>
      </div>
      </ChatBridge>
    </FilterProvider>
  );
}
