"use client";

import { useEffect, useRef, useState } from "react";
import BpmnViewer from "bpmn-js/lib/Viewer";
import Button from "@mui/material/Button";
import "bpmn-js/dist/assets/diagram-js.css";
import "bpmn-js/dist/assets/bpmn-font/css/bpmn.css";
import ZoomScrollModule from "diagram-js/lib/navigation/zoomscroll";
import MoveCanvasModule from "diagram-js/lib/navigation/movecanvas";


export type FlowMetric = {
  from?: string;            
  to?: string;              
  value: number;            // tempo medio (min)
  flowIds?: string[];       // sequenceFlowId dal backend
};

type Props = {
  file?: File | null;
  url?: string;
  height?: number;
  title?: string;
  flows?: FlowMetric[];
  minStroke?: number;
  maxStroke?: number;
  neutralColor?: string;
  enableHeat?: boolean;     
  onClose?: () => void;
};

export default function BpmnViewerBox({
  file,
  url,
  height = 600,
  title = "BPMN Viewer",
  flows = [],
  minStroke = 2,
  maxStroke = 8,
  neutralColor = "#7f8c8d",
  enableHeat = false,       // default: non colorare (così il primo viewer resta nero)
  onClose,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<InstanceType<typeof BpmnViewer> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isReady, setIsReady] = useState(false);

  // cache (chiavi "src__dst") -> elemento sequenceFlow
  const flowCacheRef = useRef<Map<string, any> | null>(null);

  // --- utils
  const getCanvas = () => (viewerRef.current?.get("canvas") as any) ?? null;

  const keysFor = (el: any): string[] => {
    const out: string[] = [];
    const id: string | undefined = el?.id;
    const name: string | undefined = el?.businessObject?.name;
    if (typeof id === "string" && id.trim()) out.push(id.trim());
    if (typeof name === "string" && name.trim()) out.push(name.trim());
    return Array.from(new Set(out));
  };

  const buildFlowCache = () => {
    if (!viewerRef.current) return;
    const elementRegistry = viewerRef.current.get("elementRegistry") as any;
    const allSeq = elementRegistry.filter((e: any) => e.type === "bpmn:SequenceFlow");

    const map = new Map<string, any>();
    allSeq.forEach((sf: any) => {
      const src = sf.businessObject?.sourceRef;
      const tgt = sf.businessObject?.targetRef;
      const srcKeys = keysFor(src);
      const tgtKeys = keysFor(tgt);
      for (const sk of srcKeys) {
        for (const tk of tgtKeys) {
          map.set(`${sk}__${tk}`, sf);
        }
      }
    });

    flowCacheRef.current = map;
  };

  const resetAllSequenceFlowsMarkers = () => {
    if (!viewerRef.current) return;
    const elementRegistry = viewerRef.current.get("elementRegistry") as any;
    const canvas = viewerRef.current.get("canvas") as any;
    const allSeq = elementRegistry.filter((e: any) => e.type === "bpmn:SequenceFlow");

    const heatClasses = ["heat-none","heat-0","heat-1","heat-2","heat-3","heat-4","heat-5"];
    allSeq.forEach((sf: any) => {
      heatClasses.forEach((cls) => canvas.removeMarker(sf.id, cls));
      // non aggiungo 'heat-none' se enableHeat=false → viewer resta black default
      if (enableHeat) canvas.addMarker(sf.id, "heat-none");
    });
  };

  // Bucket a soglie fisse (in minuti)
  const bucketOf = (v: number) => {
    if (!Number.isFinite(v)) return 0;
    if (v <= 0) return 0;
    if (v <= 5) return 1;
    if (v <= 10) return 2;
    if (v <= 20) return 3;
    if (v <= 40) return 4;
    return 5;
  };

  const applyHeatMarkers = () => {
    if (!enableHeat) return;        // non colorare se non richiesto
    if (!viewerRef.current) return;
    if (!flows?.length) return;

    const canvas = viewerRef.current.get("canvas") as any;
    const elementRegistry = viewerRef.current.get("elementRegistry") as any;
    const cache = flowCacheRef.current;

    let notFound = 0;

    flows.forEach((f) => {
      const bucket = bucketOf(f.value);

      // 1) se ho flowIds dal backend, uso quelli (più robusto)
      if (f.flowIds && f.flowIds.length) {
        f.flowIds.forEach((fid) => {
          const shape = elementRegistry.get(fid);
          if (!shape) {
            notFound++;
            return;
          }
          canvas.removeMarker(fid, "heat-none");
          canvas.addMarker(fid, `heat-${bucket}`);
        });
        return;
      }

      // 2) fallback: match by (from,to) su cache
      const from = String(f.from ?? "").trim();
      const to   = String(f.to ?? "").trim();
      if (!from || !to || !cache) return;

      const key = `${from}__${to}`;
      const sf = cache.get(key);
      if (!sf) {
        notFound++;
        return;
      }
      canvas.removeMarker(sf.id, "heat-none");
      canvas.addMarker(sf.id, `heat-${bucket}`);
    });

    if (notFound) {
      console.warn(`Flow non trovato per ${notFound} elementi (flowIds mancanti o mismatch nome/id).`);
    }
  };

  // --- mount viewer
  useEffect(() => {
    if (!containerRef.current) return;
    viewerRef.current = new BpmnViewer({
    container: containerRef.current,
    additionalModules: [
      ZoomScrollModule,    // zoom con rotella/trackpad (Ctrl+wheel)
      MoveCanvasModule     // pan/trascina la canvas
    ],
    // opzionale: abilita tasti + / - e 0 per il fit
    keyboard: { bindTo: document }
  });


    return () => {
      viewerRef.current?.destroy();
      viewerRef.current = null;
      flowCacheRef.current = null;
    };
  }, []);

  // --- load xml
  useEffect(() => {
    const load = async () => {
      if (!viewerRef.current) return;
      setError(null);
      setIsReady(false);
      flowCacheRef.current = null;

      try {
        let xml: string | null = null;
        if (file) xml = await file.text();
        else if (url) xml = await (await fetch(url)).text();
        if (!xml) return;

        await viewerRef.current.importXML(xml);
        const canvas = viewerRef.current.get("canvas") as any;
        canvas.zoom("fit-viewport", "auto");
        buildFlowCache();
        setIsReady(true);
      } catch (e) {
        console.error("Errore importXML:", e);
        setError("Impossibile caricare il file BPMN. Verifica che sia valido BPMN 2.0.");
      }
    };
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [file, url]);

  // --- apply heat when ready or flows change
  useEffect(() => {
    if (!isReady) return;
    resetAllSequenceFlowsMarkers();
    applyHeatMarkers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isReady, enableHeat, JSON.stringify(flows)]);

  // --- zoom
  const zoomIn  = () => { const c = getCanvas(); if (c) c.zoom(c.zoom() * 1.2); };
  const zoomOut = () => { const c = getCanvas(); if (c) c.zoom(c.zoom() / 1.2); };
  const zoomFit = () => { const c = getCanvas(); if (c) c.zoom("fit-viewport", "auto"); };

  return (
    <div className="w-full mx-auto">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-800">{title}</h2>
        <div className="flex items-center gap-2">
          <Button variant="outlined" onClick={zoomOut}>-</Button>
          <Button variant="outlined" onClick={zoomIn}>+</Button>
          <Button variant="outlined" onClick={zoomFit}>Fit</Button>
        </div>
      </div>

      <div
        ref={containerRef}
        className="w-full border border-gray-300 rounded-md bg-white"
        style={{ height }}
      />

      {error && <div className="text-red-600 text-sm mt-3">{error}</div>}
      {!error && enableHeat && !!flows?.length && (
        <p className="text-xs text-gray-600 mt-3">
          Bottleneck analysis based on waiting times between conseuqent activities.
          The waiting times shown are average values per traces.
          <br></br>
         The color gradient and the thickness of the arrow indicates the severity of the waiting time: <br></br>
         thin and green arrows indicate almost absent waiting times, while thick and red arrows indicate long waiting times.
        </p>
      )}
    </div>
  );
}
