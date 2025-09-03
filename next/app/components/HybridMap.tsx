// app/components/HybridMap.tsx
"use client";

import { useState, useEffect } from "react";
import {
  Map as KakaoMap,
  MapMarker,
  MapInfoWindow,
} from "react-kakao-maps-sdk";
import Papa from "papaparse";
import type { Property, NaverProperty, SamProperty } from "../types";
import KakaoScript from "./KakaoScript";

/*────────────────── 헬퍼 ──────────────────*/
const coordKey = (lat: number, lng: number) =>
  `${Math.round(lat * 1e4)}/${Math.round(lng * 1e4)}`; // 소수 4자리(≈11 m)

const pinColor = (occ: number) => {
  if (occ > 80) return "green";
  if (occ > 60) return "blue";
  if (occ > 40) return "yellow";
  if (occ > 20) return "orange";
  return "red";
};

// 겹치는 그룹의 색상 결정 (삼삼엠투 평균 예약률 기준)
const clusterColor = (occ: number) => {
  if (occ > 80) return "green";
  if (occ > 60) return "blue";
  if (occ > 40) return "yellow";
  if (occ > 20) return "orange";
  return "red";
};

const monthlyRevenue = (p: SamProperty) =>
  (p.using_fee ?? 0) * 4 * ((p.occupancy_rate_percent ?? 0) / 100);

// 삼삼엠투: 평 → 제곱미터 변환
const toM2 = (pyeong: number | null | undefined) =>
  pyeong == null ? null : Math.round(pyeong * 3.3058);

// 네이버: 제곱미터 → 평 변환
const toPyeong = (m2: number | null | undefined) =>
  m2 == null ? null : Math.round((m2 / 3.3058) * 10) / 10; // 소수 1자리

const fmt = (n: number | null | undefined, unit = "") =>
  n == null ? "—" : `${n.toLocaleString()}${unit}`;

/*────────────────── 컴포넌트 ──────────────────*/
export default function HybridMap() {
  const [groups, setGroups] = useState<Map<string, Property[]>>(new Map());
  const [selected, setSelected] = useState<Property[] | null>(null);

  /* CSV 로드 */
  useEffect(() => {
    (async () => {
      const [naverCsv, samCsv] = await Promise.all([
        fetch("/naver/naver_20250903_043133_final.csv").then((r) => r.text()),
        fetch("/reservation/reservation_4w_250903.csv").then((r) => r.text()),
      ]);

      /* 네이버 */
      const nRows = Papa.parse<NaverProperty>(naverCsv, {
        header: true,
        dynamicTyping: true,
        skipEmptyLines: true,
      }).data.filter(
        (r) => typeof r.위도 === "number" && typeof r.경도 === "number"
      );

      const nProps: Property[] = nRows.map((r) => ({
        id: r.매물ID,
        source: "naver",
        raw: r,
        title: r.매물제목 ?? "—",
        lat: r.위도,
        lng: r.경도,
        addr: r.주소 ?? "—",
        deposit: r.보증금 ?? undefined,
        rent: r.월세 ?? undefined,
      }));

      /* 삼삼엠투 */
      const sRows = Papa.parse<SamProperty>(samCsv, {
        header: true,
        dynamicTyping: true,
        skipEmptyLines: true,
      }).data.filter(
        (r) => typeof r.lat === "number" && typeof r.lng === "number"
      );

      const sProps: Property[] = sRows.map((r) => ({
        id: String(r.rid),
        source: "sam",
        raw: r,
        title: r.room_name ?? "—",
        lat: r.lat,
        lng: r.lng,
        addr: r.addr_street ?? "—",
        deposit: r.using_fee ?? undefined,
        occupancy: r.occupancy_rate_percent ?? undefined,
      }));

      /* 좌표별 그룹 */
      const map = new Map<string, Property[]>();
      [...nProps, ...sProps].forEach((p) => {
        const k = coordKey(p.lat, p.lng);
        if (!map.has(k)) map.set(k, []);
        map.get(k)!.push(p);
      });
      setGroups(map);
    })();
  }, []);

  /* 마커 아이콘 */
  const iconOf = (g: Property[]) => {
    const samList = g.filter((p) => p.source === "sam");
    const naverList = g.filter((p) => p.source === "naver");

    // 1) 네이버 + 삼삼엠투 겹침 → 삼삼엠투 평균 예약률로 색상 결정
    if (samList.length && naverList.length) {
      const avgOcc =
        samList.reduce((sum, p) => sum + (p.occupancy ?? 0), 0) /
        samList.length;
      return `/home-${clusterColor(avgOcc)}.svg`;
    }

    // 2) 삼삼엠투 단독 → 그룹 평균 예약률로 색상 결정
    if (samList.length) {
      const avgOcc =
        samList.reduce((sum, p) => sum + (p.occupancy ?? 0), 0) /
        samList.length;
      return `/pin-${pinColor(avgOcc)}.svg`;
    }

    // 3) 네이버 단독
    return "/home-default.svg";
  };

  /* InfoWindow 토글 */
  const openInfo = (g: Property[]) => {
    setSelected(null);
    requestAnimationFrame(() => setSelected(g));
  };

  /* 네이버 평균 월세 계산 (해당 그룹) */
  const getNaverAvgRent = (g: Property[]) => {
    const navers = g.filter((p) => p.source === "naver");
    if (!navers.length) return null;
    return navers.reduce((s, p) => s + (p.rent ?? 0), 0) / navers.length;
  };

  /*────────────────── 렌더 ──────────────────*/
  return (
    <>
      <KakaoScript />
      <KakaoMap
        center={{ lat: 37.5665, lng: 126.978 }}
        level={6}
        style={{ width: "100%", height: "100vh" }}
      >
        {/* 그룹별 마커 */}
        {Array.from(groups.entries()).map(([k, g]) => {
          const [lat, lng] = k.split("/").map((v) => Number(v) / 1e4);
          return (
            <MapMarker
              key={k}
              position={{ lat, lng }}
              image={{
                src: iconOf(g),
                size: { width: 32, height: 32 },
                options: { offset: { x: 16, y: 32 } },
              }}
              onClick={() => openInfo(g)}
            />
          );
        })}

        {/* InfoWindow */}
        {selected && (
          <MapInfoWindow
            key={`info-${selected[0].id}-${Date.now()}`}
            position={{ lat: selected[0].lat, lng: selected[0].lng }}
            removable
            onCloseClick={() => setSelected(null)}
          >
            {/* 스크롤 가능 영역 */}
            <div
              style={{
                padding: 16,
                minWidth: 300,
                maxWidth: 520,
                maxHeight: "60vh",
                overflowY: "auto",
                fontSize: 14,
                lineHeight: 1.4,
              }}
            >
              {selected.map((p, idx) =>
                p.source === "naver" ? (
                  /* ─── 네이버 ─── */
                  <div
                    key={`naver-${p.id}-${idx}`}
                    style={{ marginBottom: 12 }}
                  >
                    <strong style={{ color: "#15803d" }}>네이버</strong>
                    <br />
                    매물명: {(p.raw as NaverProperty).매물제목}
                    <br />
                    주소: {(p.raw as NaverProperty).주소}
                    <br />
                    전용면적:{" "}
                    {fmt(
                      toPyeong((p.raw as NaverProperty).전용면적),
                      "평"
                    )} / {fmt((p.raw as NaverProperty).전용면적, "㎡")}
                    <br />
                    보증금: {fmt((p.raw as NaverProperty).보증금, "만 원")}
                    <br />
                    월세: {fmt((p.raw as NaverProperty).월세, "만 원")}
                    <br />
                    동일주소 매물수: {(p.raw as NaverProperty).동일주소매물수}
                    <br />
                    최대보증금:{" "}
                    {fmt((p.raw as NaverProperty).동일주소_최대보증금, "만 원")}
                    <br />
                    최소보증금:{" "}
                    {fmt((p.raw as NaverProperty).동일주소_최소보증금, "만 원")}
                    <br />
                    최대월세:{" "}
                    {fmt((p.raw as NaverProperty).동일주소_최대월세, "만 원")}
                    <br />
                    최소월세:{" "}
                    {fmt((p.raw as NaverProperty).동일주소_최소월세, "만 원")}
                  </div>
                ) : (
                  /* ─── 삼삼엠투 ─── */
                  <div key={`sam-${p.id}-${idx}`} style={{ marginBottom: 12 }}>
                    <strong style={{ color: "#1d4ed8" }}>삼삼엠투</strong>
                    <br />
                    매물명: {(p.raw as SamProperty).room_name}
                    <br />
                    주소: {(p.raw as SamProperty).addr_street}
                    <br />
                    평형: {fmt((p.raw as SamProperty).pyeong_size, "평")} /{" "}
                    {fmt(toM2((p.raw as SamProperty).pyeong_size), "㎡")}
                    <br />
                    1주당 금액: {fmt((p.raw as SamProperty).using_fee, "원")}
                    <br />
                    예약률:{" "}
                    {fmt((p.raw as SamProperty).occupancy_rate_percent, "%")}
                    <br />
                    방/욕실/주방/거실: {(p.raw as SamProperty).room_cnt}/
                    {(p.raw as SamProperty).bathroom_cnt}/
                    {(p.raw as SamProperty).cookroom_cnt}/
                    {(p.raw as SamProperty).sittingroom_cnt}
                    <br />
                    장기 할인율: {(p.raw as SamProperty).longterm_discount_per}%
                    <br />
                    얼리버드 할인율: {(p.raw as SamProperty).early_discount_per}
                    %<br />
                    <em style={{ color: "#16a34a", fontWeight: 600 }}>
                      예상 월 수익:{" "}
                      {monthlyRevenue(p.raw as SamProperty).toLocaleString()}원
                    </em>
                    {(() => {
                      const naverAvg = getNaverAvgRent(selected);
                      if (naverAvg == null) {
                        return (
                          <>
                            <br />
                            <span style={{ color: "#666" }}>
                              (네이버 매물 없음 - 비교 불가)
                            </span>
                          </>
                        );
                      }
                      const diff =
                        monthlyRevenue(p.raw as SamProperty) -
                        naverAvg * 10_000; // 만 원 → 원 변환
                      return (
                        <>
                          <br />
                          <span style={{ fontSize: 12, color: "#666" }}>
                            네이버 평균 월세: {naverAvg.toLocaleString()}만원
                          </span>
                          <br />
                          <span
                            style={{
                              color: diff >= 0 ? "#16a34a" : "#dc2626",
                              fontWeight: 600,
                            }}
                          >
                            개별 수익 차액: {diff >= 0 ? "+" : ""}
                            {diff.toLocaleString()}원
                          </span>
                        </>
                      );
                    })()}
                  </div>
                )
              )}
            </div>
          </MapInfoWindow>
        )}
      </KakaoMap>
    </>
  );
}
