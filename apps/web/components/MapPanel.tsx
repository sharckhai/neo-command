"use client";

import { useEffect, useRef, useCallback } from "react";
import type { Facility } from "../lib/types";
import { CAP } from "../lib/capabilities";
import { GR } from "../lib/geo";

type DesertRegion = {
  region: string;
  capability: string;
};

type MapPanelProps = {
  facilities: Facility[];
  selCap?: string | null;
  desertRegions?: DesertRegion[];
  planFacs?: Facility[];
  onFacClick?: (fac: Facility) => void;
};

export default function MapPanel({
  facilities,
  selCap,
  desertRegions,
  planFacs,
  onFacClick,
}: MapPanelProps) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<any>(null);
  const mapboxRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const circlesRef = useRef<any[]>([]);

  // Initialize map once
  useEffect(() => {
    let isMounted = true;

    async function initMap() {
      const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;
      if (!token || !mapContainerRef.current || mapRef.current) return;

      const mapboxgl = await import("mapbox-gl");
      mapboxgl.default.accessToken = token;
      mapboxRef.current = mapboxgl.default;

      mapRef.current = new mapboxgl.default.Map({
        container: mapContainerRef.current,
        style: "mapbox://styles/mapbox/dark-v11",
        center: [-1.0232, 7.9465],
        zoom: 5.5,
      });

      mapRef.current.addControl(
        new mapboxgl.default.NavigationControl(),
        "top-right"
      );
    }

    initMap();

    return () => {
      isMounted = false;
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  // Update markers and overlays when data changes
  useEffect(() => {
    if (!mapRef.current || !mapboxRef.current) return;

    // Clear previous markers and circles
    for (const m of markersRef.current) m.remove();
    markersRef.current = [];
    for (const c of circlesRef.current) c.remove();
    circlesRef.current = [];

    const planIdSet = new Set((planFacs || []).map((f) => f.id));

    // Desert zone overlays — use Mapbox circles via markers
    if (desertRegions) {
      for (const d of desertRegions) {
        const coords = GR[d.region?.toLowerCase()];
        if (!coords) continue;

        const el = document.createElement("div");
        el.style.width = "80px";
        el.style.height = "80px";
        el.style.borderRadius = "50%";
        el.style.border = "2px dashed rgba(255,42,42,0.5)";
        el.style.background = "rgba(255,42,42,0.08)";
        el.title = `Desert: ${d.region} — Missing ${(CAP[d.capability] || {}).l || d.capability}`;

        const marker = new mapboxRef.current.Marker({ element: el })
          .setLngLat([coords[1], coords[0]])
          .addTo(mapRef.current);
        circlesRef.current.push(marker);
      }
    }

    // Plan facility highlights
    if (planFacs) {
      for (const f of planFacs) {
        if (!f.lat || !f.lng) continue;
        const el = document.createElement("div");
        el.style.width = "20px";
        el.style.height = "20px";
        el.style.borderRadius = "50%";
        el.style.border = "2px solid #10b981";
        el.style.background = "rgba(16,185,129,0.15)";
        const marker = new mapboxRef.current.Marker({ element: el })
          .setLngLat([f.lng, f.lat])
          .addTo(mapRef.current);
        circlesRef.current.push(marker);
      }
    }

    // Facility markers
    const bounds =
      facilities.length > 0 ? new mapboxRef.current.LngLatBounds() : null;

    for (const f of facilities) {
      if (!f.lat || !f.lng) continue;

      const hasCap =
        f.capabilities && selCap
          ? f.capabilities[selCap] === true ||
            (typeof f.capabilities[selCap] === "number" &&
              (f.capabilities[selCap] as number) > 0)
          : null;
      const isPlan = planIdSet.has(f.id);
      const anomalyCount = (f.anomalies || []).length;

      // Color logic
      let col: string;
      if (isPlan) col = "#10b981";
      else if (hasCap === true) col = "#10b981";
      else if (hasCap === false) col = "#ef4444";
      else if (anomalyCount > 0) col = "#f59e0b";
      else col = "#e2853e";

      const r = isPlan ? 14 : hasCap === true ? 12 : 10;

      const el = document.createElement("div");
      el.style.width = `${r}px`;
      el.style.height = `${r}px`;
      el.style.borderRadius = "999px";
      el.style.background = col;
      el.style.boxShadow = `0 0 0 ${isPlan ? 5 : 4}px ${col}33`;
      el.style.cursor = "pointer";
      el.title = f.name;

      const marker = new mapboxRef.current.Marker({ element: el })
        .setLngLat([f.lng, f.lat])
        .addTo(mapRef.current);

      if (onFacClick) {
        el.addEventListener("click", () => onFacClick(f));
      }

      // Popup with capability badges
      const capBadges = f.capabilities
        ? Object.entries(f.capabilities)
            .filter(([, v]) => v === true)
            .slice(0, 4)
            .map(
              ([k]) =>
                `<span style="display:inline-block;padding:1px 4px;margin:1px;border-radius:3px;background:rgba(226,133,62,.1);color:#e2853e;font-size:8px">${(CAP[k] || {}).i || ""} ${(CAP[k] || {}).l || k}</span>`
            )
            .join("")
        : "";

      const popup = new mapboxRef.current.Popup({
        offset: 8,
        closeButton: false,
      }).setHTML(
        `<div style="min-width:140px;font-family:IBM Plex Sans,sans-serif">` +
          `<b style="font-size:12px">${f.name}</b>` +
          `<div style="color:#8899ad;font-size:10px;margin:2px 0">${f.city || ""} ${f.region ? "· " + f.region : ""}</div>` +
          capBadges +
          (isPlan
            ? '<div style="color:#10b981;font-size:10px;margin-top:4px">★ In mission plan</div>'
            : "") +
          `</div>`
      );
      marker.setPopup(popup);

      markersRef.current.push(marker);
      bounds?.extend([f.lng, f.lat]);
    }

    // Fit bounds to visible facilities
    if (bounds && facilities.some((f) => f.lat && f.lng)) {
      mapRef.current.fitBounds(bounds, { padding: 40, maxZoom: 8 });
    }
  }, [facilities, selCap, desertRegions, planFacs, onFacClick]);

  return (
    <div
      ref={mapContainerRef}
      style={{ width: "100%", height: "100%", borderRadius: "var(--rd)" }}
      role="application"
      aria-label="Ghana health facility map"
    />
  );
}
