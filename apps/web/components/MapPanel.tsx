"use client";

import { useEffect, useRef, useState } from "react";
import { ChatResponse, FacilitySummary } from "../lib/types";

const REGION_CENTERS: Record<string, [number, number]> = {
  "Greater Accra": [5.6037, -0.187],
  Ashanti: [6.6885, -1.6244],
  Northern: [9.4075, -0.8533],
  "Upper East": [10.7867, -0.8514],
  "Upper West": [10.0601, -2.5019],
  Volta: [6.6008, 0.4713],
  Western: [4.934, -1.7137],
  "Western North": [6.2032, -2.4911],
  Eastern: [6.0897, -0.2591],
  Central: [5.1053, -1.2466],
  Bono: [7.3349, -2.3123],
  "Bono East": [7.5897, -1.9298],
  Ahafo: [6.8045, -2.5196],
  Oti: [8.0624, 0.5527],
  Savannah: [9.0833, -1.8167],
  "North East": [10.517, -0.363],
};

export default function MapPanel() {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<any>(null);
  const mapboxRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const [status, setStatus] = useState<string>("Initializing map...");
  const [facilityCount, setFacilityCount] = useState<number>(0);

  const setMarkers = (facilities: FacilitySummary[]) => {
    if (!mapRef.current || !mapboxRef.current) return;
    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = [];
    facilities.forEach((facility) => {
      if (facility.lat == null || facility.lng == null) return;
      const el = document.createElement("div");
      el.style.width = "10px";
      el.style.height = "10px";
      el.style.borderRadius = "999px";
      el.style.background = "#d18f4f";
      el.style.boxShadow = "0 0 0 4px rgba(209,143,79,0.2)";
      const marker = new mapboxRef.current.Marker(el)
        .setLngLat([facility.lng, facility.lat])
        .addTo(mapRef.current);
      markersRef.current.push(marker);
    });
    setFacilityCount(facilities.length);
  };

  useEffect(() => {
    let isMounted = true;
    async function initMap() {
      const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;
      if (!token) {
        setStatus("Mapbox token missing. Set NEXT_PUBLIC_MAPBOX_TOKEN.");
        return;
      }
      if (!mapContainerRef.current || mapRef.current) {
        return;
      }
      const mapboxgl = await import("mapbox-gl");
      mapboxgl.default.accessToken = token;
      mapboxRef.current = mapboxgl.default;
      mapRef.current = new mapboxgl.default.Map({
        container: mapContainerRef.current,
        style: "mapbox://styles/mapbox/dark-v11",
        center: [-1.0232, 7.9465],
        zoom: 5.5,
      });
      mapRef.current.addControl(new mapboxgl.default.NavigationControl(), "top-right");
      if (isMounted) {
        setStatus("Live map ready");
      }
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

  useEffect(() => {
    async function loadFacilities() {
      try {
        const res = await fetch("/api/facilities");
        if (!res.ok) return;
        const data = (await res.json()) as FacilitySummary[];
        setMarkers(data);
      } catch {
        // ignore
      }
    }
    loadFacilities();
  }, []);

  useEffect(() => {
    const handler = (event: Event) => {
      const detail = (event as CustomEvent<ChatResponse>).detail;
      if (!detail) return;
      if (detail.facilities && detail.facilities.length) {
        setMarkers(detail.facilities);
      }
      detail.map_actions.forEach((action) => {
        if (action.type === "zoom_region" && action.data?.region) {
          const region = action.data.region as string;
          const center = REGION_CENTERS[region];
          if (center && mapRef.current) {
            mapRef.current.flyTo({ center: [center[1], center[0]], zoom: 6.5 });
            setStatus(`Focused on ${region}`);
          }
        }
      });
    };
    window.addEventListener("map-actions", handler as EventListener);
    return () => window.removeEventListener("map-actions", handler as EventListener);
  }, []);

  return (
    <section className="panel map-panel">
      <div className="map-header">
        <div>
          <strong>Ghana Field View</strong>
          <div>{status}</div>
        </div>
        <div>{facilityCount} facilities</div>
      </div>
      <div ref={mapContainerRef} className="map-container" />
      <div className="map-overlay">
        <div className="map-pill">Facility density</div>
        <div className="map-pill">Trust signals</div>
      </div>
    </section>
  );
}
