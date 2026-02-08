"use client";

import { useEffect, useRef, useState } from "react";

export default function MapPanel() {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<any>(null);
  const [status, setStatus] = useState<string>("Initializing map...");

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

  return (
    <section className="panel map-panel">
      <div className="map-header">
        <div>
          <strong>Ghana Field View</strong>
          <div>{status}</div>
        </div>
        <div>VirtueCommand Atlas</div>
      </div>
      <div ref={mapContainerRef} className="map-container" />
      <div className="map-overlay">
        <div className="map-pill">Facility density</div>
        <div className="map-pill">Trust signals</div>
      </div>
    </section>
  );
}
