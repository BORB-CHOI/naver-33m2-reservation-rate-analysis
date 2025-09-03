// app/premium/components/PremiumMap.tsx
"use client";

import { useState, useEffect } from "react";
import {
  Map as KakaoMap,
  MapMarker,
  MapInfoWindow,
} from "react-kakao-maps-sdk";
import Papa from "papaparse";
import type { Property, NaverProperty, SeoulProperty } from "../../types";
import KakaoScript from "../../components/KakaoScript";

/*────────────────── 헬퍼 ──────────────────*/
// 더 관대한 좌표 그룹핑 (소수 3자리 → 약 111m 오차)
const coordKey = (lat: number, lng: number) =>
  `${Math.round(lat * 1e3)}/${Math.round(lng * 1e3)}`; // 소수 3자리(≈111 m)

// 1주당 금액에 따른 핀 색상 결정
const weeklyFeeColor = (weeklyFee: number) => {
  if (weeklyFee >= 300000) return "green"; // 30만 이상: 초록
  return "purple"; // 30만 미만: 보라
};

// 서울 오피스텔 월 수익 계산 (기본 공식)
const monthlyRevenue = (p: SeoulProperty) => (p.using_fee ?? 0) * 4;

// 수익률 계산: (서울오피스텔 금액 * 4 - 네이버 월세) / 네이버 월세 * 100
const calculateProfitRate = (seoulRevenue: number, naverRent: number) => {
  if (naverRent === 0) return 0;
  return ((seoulRevenue - naverRent * 10_000) / (naverRent * 10_000)) * 100;
};

// 서울오피스텔: 평 → 제곱미터 변환
const toM2 = (pyeong: number | null | undefined) =>
  pyeong == null ? null : Math.round(pyeong * 3.3058);

// 네이버: 제곱미터 → 평 변환
const toPyeong = (m2: number | null | undefined) =>
  m2 == null ? null : Math.round((m2 / 3.3058) * 10) / 10; // 소수 1자리

const fmt = (n: number | null | undefined, unit = "") =>
  n == null ? "—" : `${n.toLocaleString()}${unit}`;

/*────────────────── 컴포넌트 ──────────────────*/
export default function PremiumMap() {
  const [groups, setGroups] = useState<Map<string, Property[]>>(new Map());
  const [selected, setSelected] = useState<Property[] | null>(null);

  /* CSV 로드 */
  useEffect(() => {
    (async () => {
      const [naverCsv, seoulCsv] = await Promise.all([
        fetch("/naver/naver_20250808_035438_final.csv").then((r) => r.text()),
        fetch("/room/room_250808.csv").then((r) => r.text()),
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

      /* 서울 오피스텔 */
      const sRows = Papa.parse<SeoulProperty>(seoulCsv, {
        header: true,
        dynamicTyping: true,
        skipEmptyLines: true,
      }).data.filter(
        (r) => typeof r.lat === "number" && typeof r.lng === "number"
      );

      const sProps: Property[] = sRows.map((r) => ({
        id: String(r.rid),
        source: "seoul",
        raw: r,
        title: r.room_name ?? "—",
        lat: r.lat,
        lng: r.lng,
        addr: r.addr_street ?? "—",
        deposit: r.using_fee ?? undefined,
        occupancy: undefined, // 1주당 금액 기준으로 판단
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
    const seoulList = g.filter((p) => p.source === "seoul");
    const naverList = g.filter((p) => p.source === "naver");

    // 1) 네이버 + 서울오피스텔 겹침 → 서울오피스텔 1주당 금액 기준 색상
    if (seoulList.length && naverList.length) {
      // 서울오피스텔 평균 1주당 금액 계산
      const avgWeeklyFee =
        seoulList.reduce((sum, p) => {
          return sum + ((p.raw as SeoulProperty).using_fee ?? 0);
        }, 0) / seoulList.length;

      return `/pin-${weeklyFeeColor(avgWeeklyFee)}.svg`;
    }

    // 2) 서울오피스텔 단독 → 1주당 금액 기준 색상
    if (seoulList.length) {
      const avgWeeklyFee =
        seoulList.reduce((sum, p) => {
          return sum + ((p.raw as SeoulProperty).using_fee ?? 0);
        }, 0) / seoulList.length;

      return `/pin-${weeklyFeeColor(avgWeeklyFee)}.svg`;
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

  // 마커 렌더링 순서 조정을 위한 그룹 분리
  const naverOnlyGroups = Array.from(groups.entries()).filter(([, g]) => {
    const seoulList = g.filter((p) => p.source === "seoul");
    const naverList = g.filter((p) => p.source === "naver");
    return naverList.length > 0 && seoulList.length === 0;
  });

  const seoulGroups = Array.from(groups.entries()).filter(([, g]) => {
    const seoulList = g.filter((p) => p.source === "seoul");
    return seoulList.length > 0;
  });

  /*────────────────── 렌더 ──────────────────*/
  return (
    <>
      <KakaoScript />

      {/* 범례 */}
      <div
        style={{
          position: "absolute",
          top: 10,
          right: 10,
          zIndex: 1000,
          backgroundColor: "white",
          padding: "15px",
          borderRadius: "8px",
          boxShadow: "0 2px 10px rgba(0,0,0,0.2)",
          fontSize: "14px",
        }}
      >
        <div
          style={{ fontWeight: "bold", marginBottom: "10px", color: "#333" }}
        >
          1주당 금액 기준
        </div>
        <div
          style={{ display: "flex", alignItems: "center", marginBottom: "8px" }}
        >
          <div
            style={{
              width: "16px",
              height: "16px",
              backgroundColor: "#22c55e",
              borderRadius: "50%",
              marginRight: "8px",
            }}
          ></div>
          <span>30만원 이상 (초록)</span>
        </div>
        <div
          style={{ display: "flex", alignItems: "center", marginBottom: "8px" }}
        >
          <div
            style={{
              width: "16px",
              height: "16px",
              backgroundColor: "#9333ea",
              borderRadius: "50%",
              marginRight: "8px",
            }}
          ></div>
          <span>30만원 미만 (보라)</span>
        </div>
        <div style={{ display: "flex", alignItems: "center" }}>
          <div
            style={{
              width: "16px",
              height: "16px",
              backgroundColor: "#6b7280",
              borderRadius: "50%",
              marginRight: "8px",
            }}
          ></div>
          <span>네이버 매물 (회색)</span>
        </div>
      </div>

      <KakaoMap
        center={{ lat: 37.5665, lng: 126.978 }}
        level={6}
        style={{ width: "100%", height: "100vh" }}
      >
        {/* 네이버 단독 마커 먼저 렌더링 (뒤에 위치) */}
        {naverOnlyGroups.map(([k, g]) => {
          const [lat, lng] = k.split("/").map((v) => Number(v) / 1e3);
          return (
            <MapMarker
              key={`naver-${k}`}
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

        {/* 서울오피스텔 포함 마커 나중에 렌더링 (앞에 위치) */}
        {seoulGroups.map(([k, g]) => {
          const [lat, lng] = k.split("/").map((v) => Number(v) / 1e3);
          return (
            <MapMarker
              key={`seoul-${k}`}
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
              <div
                style={{ marginBottom: 10, fontWeight: "bold", color: "#333" }}
              >
                매물 {selected.length}건 - 1주당 금액 기준
              </div>

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
                  /* ─── 서울 오피스텔 ─── */
                  <div
                    key={`seoul-${p.id}-${idx}`}
                    style={{ marginBottom: 12 }}
                  >
                    <strong
                      style={{
                        color:
                          (p.raw as SeoulProperty).using_fee &&
                          (p.raw as SeoulProperty).using_fee! >= 300000
                            ? "#22c55e" // 30만 이상: 초록
                            : "#9333ea", // 30만 미만: 보라
                      }}
                    >
                      서울 오피스텔{" "}
                      {(p.raw as SeoulProperty).using_fee &&
                      (p.raw as SeoulProperty).using_fee! >= 300000
                        ? "(프리미엄)"
                        : "(일반)"}
                    </strong>
                    <br />
                    매물명: {(p.raw as SeoulProperty).room_name}
                    <br />
                    주소: {(p.raw as SeoulProperty).addr_street}
                    <br />
                    평형: {fmt(
                      (p.raw as SeoulProperty).pyeong_size,
                      "평"
                    )} / {fmt(toM2((p.raw as SeoulProperty).pyeong_size), "㎡")}
                    <br />
                    <strong
                      style={{
                        color:
                          (p.raw as SeoulProperty).using_fee &&
                          (p.raw as SeoulProperty).using_fee! >= 300000
                            ? "#22c55e"
                            : "#9333ea",
                        fontSize: "16px",
                      }}
                    >
                      1주당 금액:{" "}
                      {fmt((p.raw as SeoulProperty).using_fee, "원")}
                    </strong>
                    <br />
                    방/욕실/주방/거실: {(p.raw as SeoulProperty).room_cnt}/
                    {(p.raw as SeoulProperty).bathroom_cnt}/
                    {(p.raw as SeoulProperty).cookroom_cnt}/
                    {(p.raw as SeoulProperty).sittingroom_cnt}
                    <br />
                    장기 할인율:{" "}
                    {(p.raw as SeoulProperty).longterm_discount_per}%
                    <br />
                    얼리버드 할인율:{" "}
                    {(p.raw as SeoulProperty).early_discount_per}
                    %<br />
                    <em style={{ color: "#16a34a", fontWeight: 600 }}>
                      월 기본 수익:{" "}
                      {monthlyRevenue(p.raw as SeoulProperty).toLocaleString()}
                      원
                    </em>
                    {(() => {
                      const naverAvg = getNaverAvgRent(selected);
                      if (naverAvg == null) {
                        return (
                          <>
                            <br />
                            <span style={{ color: "#666" }}>
                              (네이버 매물 없음 - 수익률 계산 불가)
                            </span>
                          </>
                        );
                      }

                      const revenue = monthlyRevenue(p.raw as SeoulProperty);
                      const profitRate = calculateProfitRate(revenue, naverAvg);
                      const diff = revenue - naverAvg * 10_000;

                      return (
                        <>
                          <br />
                          <span style={{ fontSize: 12, color: "#666" }}>
                            네이버 평균 월세: {naverAvg.toLocaleString()}만원
                          </span>
                          <br />
                          <span
                            style={{
                              color: profitRate >= 0 ? "#16a34a" : "#dc2626",
                              fontWeight: 600,
                            }}
                          >
                            수익률: {profitRate >= 0 ? "+" : ""}
                            {profitRate.toFixed(1)}%
                          </span>
                          <br />
                          <span
                            style={{
                              color: diff >= 0 ? "#16a34a" : "#dc2626",
                            }}
                          >
                            금액 차액: {diff >= 0 ? "+" : ""}
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
