"use client";

import React, { useMemo, useState } from "react";

type SimulationSignal = {
  name: string;
  values: number[];
};

export type SimulationSnapshot = {
  timestamps: number[];
  signals: SimulationSignal[];
};

type SimulationPanelProps = {
  title?: string;
  snapshot?: SimulationSnapshot | null;
  loading?: boolean;
  onClose?: () => void;
};

export function SimulationPanel({
  title = "Simulation Result",
  snapshot,
  loading = false,
  onClose,
}: SimulationPanelProps) {
  const hasData =
    !!snapshot &&
    Array.isArray(snapshot.timestamps) &&
    snapshot.timestamps.length > 0 &&
    Array.isArray(snapshot.signals) &&
    snapshot.signals.length > 0;

  const [selectedTab, setSelectedTab] = useState<"signals" | "json">("signals");
  const [selectedSignalName, setSelectedSignalName] = useState<string | null>(
    () => (snapshot?.signals?.[0]?.name ? snapshot.signals[0].name : null)
  );

  // keep selected signal valid when snapshot changes
  React.useEffect(() => {
    if (!snapshot?.signals?.length) {
      setSelectedSignalName(null);
      return;
    }
    if (!selectedSignalName) {
      setSelectedSignalName(snapshot.signals[0].name);
      return;
    }
    const stillThere = snapshot.signals.find((s) => s.name === selectedSignalName);
    if (!stillThere) {
      setSelectedSignalName(snapshot.signals[0].name);
    }
  }, [snapshot, selectedSignalName]);

  const selectedSignal = useMemo(() => {
    if (!hasData || !selectedSignalName) return null;
    return snapshot!.signals.find((s) => s.name === selectedSignalName) ?? null;
  }, [hasData, snapshot, selectedSignalName]);

  return (
    //<aside className="flex h-full w-full flex-col rounded-2xl bg-white/70 shadow-sm ring-1 ring-white/50 backdrop-blur">
    <aside className="flex h-full w-full flex-col rounded-2xl bg-white shadow-sm border border-slate-200">
      {/* header */}
      <div className="flex items-center justify-between rounded-t-2xl bg-[#5E3BEE] px-4 py-3 text-white">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{title}</span>
          {hasData ? (
            <span className="rounded-full bg-white/20 px-2 py-0.5 text-[10px]">
              {snapshot!.signals.length} signals
            </span>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          {loading ? (
            <span className="text-[10px] opacity-80">running…</span>
          ) : null}
          <button
            onClick={onClose}
            className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-white/10 text-xs hover:bg-white/20"
          >
            ×
          </button>
        </div>
      </div>

      {/* tabs */}
      <div className="flex gap-2 border-b bg-white/50 px-3 py-2 text-xs">
        <button
          onClick={() => setSelectedTab("signals")}
          className={`rounded-md px-3 py-1 ${
            selectedTab === "signals"
              ? "bg-white text-slate-900 shadow-sm"
              : "text-slate-500 hover:text-slate-900"
          }`}
        >
          Signals
        </button>
        <button
          onClick={() => setSelectedTab("json")}
          className={`rounded-md px-3 py-1 ${
            selectedTab === "json"
              ? "bg-white text-slate-900 shadow-sm"
              : "text-slate-500 hover:text-slate-900"
          }`}
        >
          Raw JSON
        </button>
      </div>

      {/* body */}
      <div className="flex-1 overflow-y-auto px-3 py-3">
        {!hasData ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-sm text-slate-400">
            <span>No simulation data yet.</span>
            <span className="text-[11px]">
              Run an agent tool that returns a <code>StateSnapshot</code>.
            </span>
          </div>
        ) : selectedTab === "signals" ? (
          <div className="flex h-full gap-3">
            {/* signal list */}
            <div className="w-32 shrink-0 space-y-2">
              {snapshot!.signals.map((sig) => (
                <button
                  key={sig.name}
                  onClick={() => setSelectedSignalName(sig.name)}
                  className={`flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-left text-xs ${
                    selectedSignalName === sig.name
                      ? "bg-[#5E3BEE]/10 text-slate-900 ring-1 ring-[#5E3BEE]/30"
                      : "text-slate-500 hover:bg-slate-50"
                  }`}
                >
                  <span className="truncate">{sig.name}</span>
                  <span className="text-[10px] opacity-60">{sig.values.length}</span>
                </button>
              ))}
            </div>

            {/* chart + meta */}
            <div className="flex-1 space-y-3">
              <div className="rounded-xl border bg-white/60 p-3">
                <p className="text-xs font-medium text-slate-700">
                  {selectedSignal?.name}
                </p>
                <p className="text-[10px] text-slate-400">
                  {snapshot!.timestamps.length} samples •{" "}
                  {snapshot!.timestamps[0]} –{" "}
                  {snapshot!.timestamps[snapshot!.timestamps.length - 1]}
                </p>
                <MiniLineChart
                  timestamps={snapshot!.timestamps}
                  values={selectedSignal?.values ?? []}
                />
              </div>
              <div className="grid grid-cols-3 gap-2 text-[11px] text-slate-500">
                <Stat label="Min" value={minOf(selectedSignal?.values)} />
                <Stat label="Max" value={maxOf(selectedSignal?.values)} />
                <Stat label="Last" value={lastOf(selectedSignal?.values)} />
              </div>
            </div>
          </div>
        ) : (
          <pre className="max-h-[360px] overflow-auto rounded-lg bg-slate-900/90 p-3 text-[10px] leading-tight text-slate-100">
            {JSON.stringify(snapshot, null, 2)}
          </pre>
        )}
      </div>
    </aside>
  );
}

function Stat({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="rounded-lg bg-white/50 p-2">
      <p className="text-[10px] uppercase tracking-wide text-slate-400">
        {label}
      </p>
      <p className="text-sm font-semibold text-slate-900">
        {value !== null ? value.toFixed(3) : "—"}
      </p>
    </div>
  );
}

// tiny SVG chart – no external lib
function MiniLineChart({
  timestamps,
  values,
  height = 120,
}: {
  timestamps: number[];
  values: number[];
  height?: number;
}) {
  if (!timestamps.length || !values.length) {
    return (
      <div className="mt-4 flex h-[90px] items-center justify-center rounded-md bg-slate-50 text-[10px] text-slate-400">
        No data
      </div>
    );
  }

  const width = 360;
  const minX = timestamps[0];
  const maxX = timestamps[timestamps.length - 1];
  const minY = Math.min(...values);
  const maxY = Math.max(...values);
  const spanY = maxY - minY || 1;

  const points = timestamps
    .map((t, i) => {
      const x = ((t - minX) / (maxX - minX || 1)) * (width - 20) + 10;
      const y = height - ((values[i] - minY) / spanY) * (height - 20) - 10;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="mt-3 w-full">
      <polyline
        points={points}
        fill="none"
        stroke="url(#g)"
        strokeWidth={2}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <defs>
        <linearGradient id="g" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0%" stopColor="#5E3BEE" stopOpacity="1" />
          <stop offset="100%" stopColor="#15C39A" stopOpacity="1" />
        </linearGradient>
      </defs>
    </svg>
  );
}

function minOf(arr?: number[] | null): number | null {
  if (!arr?.length) return null;
  return Math.min(...arr);
}
function maxOf(arr?: number[] | null): number | null {
  if (!arr?.length) return null;
  return Math.max(...arr);
}
function lastOf(arr?: number[] | null): number | null {
  if (!arr?.length) return null;
  return arr[arr.length - 1];
}
