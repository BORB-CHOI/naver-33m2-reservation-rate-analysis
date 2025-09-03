// app/hooks/useKakaoMap.ts
"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useKakaoLoader } from "react-kakao-maps-sdk";
import Papa from "papaparse";
import type { RoomData } from "../types";

export function useKakaoMap() {
  const [mounted, setMounted] = useState(false);
  const [rooms, setRooms] = useState<RoomData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mapRef = useRef<kakao.maps.Map | null>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  const [sdkLoading, sdkError] = useKakaoLoader({
    appkey: process.env.NEXT_PUBLIC_KAKAO_MAP_API_KEY!,
    libraries: ["clusterer", "services"],
  });

  const parseCSV = useCallback(async (file: File) => {
    if (!file.name.toLowerCase().endsWith(".csv")) {
      setError("CSV 파일만 업로드 가능합니다.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await new Promise<RoomData[]>((resolve, reject) => {
        Papa.parse<RoomData>(file, {
          header: true,
          dynamicTyping: true,
          skipEmptyLines: true,
          complete: (res) =>
            resolve(res.data.filter((r) => r.latitude && r.longitude)),
          error: (e) => reject(e),
        });
      });
      setRooms(data);
    } catch {
      setError("CSV 파싱 실패");
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    mounted,
    isReady: mounted && !sdkLoading && !sdkError,
    loading,
    error: error || (sdkError && "카카오맵 로딩 오류"),
    rooms,
    parseCSV,
    mapRef,
  };
}
